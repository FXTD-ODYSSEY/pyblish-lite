"""The Controller in a Model/View/Controller-based application

The graphical components of Pyblish Lite use this object to perform
publishing. It communicates via the Qt Signals/Slots mechanism
and has no direct connection to any graphics. This is important,
because this is how unittests are able to run without requiring
an active window manager; such as via Travis-CI.

"""

import traceback

from .vendor.Qt import QtCore

import pyblish.api
import pyblish.util
import pyblish.logic

from . import util


class Controller(QtCore.QObject):

    # Emitted when the GUI is about to start processing;
    # e.g. resetting, validating or publishing.
    about_to_process = QtCore.Signal(object, object)

    # Emitted for each process
    was_processed = QtCore.Signal(dict)

    was_discovered = QtCore.Signal(bool)
    was_reset = QtCore.Signal()
    was_validated = QtCore.Signal()
    was_published = QtCore.Signal()
    was_acted = QtCore.Signal(dict)

    # Emitted when processing has finished
    was_finished = QtCore.Signal()

    PART_COLLECT = 'collect'
    PART_VALIDATE = 'validate'
    PART_EXTRACT = 'extract'
    PART_CONFORM = 'conform'
    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)

        self.context = list()
        self.plugins = list()

        # Data internal to the GUI itself
        self.is_running = False

        # Transient state used during publishing.
        self.pair_generator = None        # Active producer of pairs
        self.current_pair = (None, None)  # Active pair
        self.current_error = None

        # This is used to track whether or not to continue
        # processing when, for example, validation has failed.
        self.processing = {
            "nextOrder": None,
            "ordersWithError": set()
        }

    def reset(self):
        """Discover plug-ins and run collection"""
        self.validated = False
        self.all_plugins = []
        self.context = pyblish.api.Context()
        self.all_plugins = pyblish.api.discover()
        # Load collectors
        self.load_plugins(True)
        # Load rest of plugins wth collected instances
        self._load()

        self.pair_generator = None
        self.current_pair = (None, None)
        self.current_error = None

        self.processing = {
            "nextOrder": None,
            "ordersWithError": set()
        }

    def load_plugins(self, load_collector=False):
        self.test = pyblish.logic.registered_test()
        self.state = {
            "nextOrder": None,
            "ordersWithError": set()
        }

        targets = pyblish.logic.registered_targets() or ["default"]

        collectors = []
        validators = []
        extractors = []
        conforms = []
        plugins = pyblish.logic.plugins_by_targets(
            self.all_plugins, targets
        )

        for plugin in plugins:
            if load_collector:
                if plugin.order < 1:
                    collectors.append(plugin)
            else:
                if plugin.order < 1:
                    continue
                elif plugin.order < 2:
                    validators.append(plugin)
                elif plugin.order < 3:
                    extractors.append(plugin)
                else:
                    conforms.append(plugin)

        if not load_collector:
            collectors = self.plugins[self.PART_COLLECT]

        self.plugins = {
            self.PART_COLLECT: collectors,
            self.PART_VALIDATE: validators,
            self.PART_EXTRACT: extractors,
            self.PART_CONFORM: conforms
        }

        self.was_discovered.emit(load_collector)

    def on_validated(self):
        pyblish.api.emit("validated", context=self.context)
        self.was_validated.emit()

    def on_published(self):
        pyblish.api.emit("published", context=self.context)
        self.was_published.emit()

    def act(self, plugin, action):
        context = self.context

        def on_next():
            result = pyblish.plugin.process(plugin, context, None, action.id)
            self.was_acted.emit(result)

        util.defer(100, on_next)

    def emit_(self, signal, kwargs):
        pyblish.api.emit(signal, **kwargs)

    def _load(self):
        """Initiate new generator and load first pair"""
        self.collect()
        self.current_error = None

    def _process(self, plugin, instance=None):
        """Produce `result` from `plugin` and `instance`

        :func:`process` shares state with :func:`_iterator` such that
        an instance/plugin pair can be fetched and processed in isolation.

        Arguments:
            plugin (pyblish.api.Plugin): Produce result using plug-in
            instance (optional, pyblish.api.Instance): Process this instance,
                if no instance is provided, context is processed.

        """

        self.processing["nextOrder"] = plugin.order

        try:
            result = pyblish.plugin.process(plugin, self.context, instance)

        except Exception as e:
            raise Exception("Unknown error: %s" % e)

        else:
            # Make note of the order at which the
            # potential error error occured.
            has_error = result["error"] is not None
            if has_error:
                self.processing["ordersWithError"].add(plugin.order)

        return result

    def _plugin_collect(self, plugins, collect=False):
        output = []
        for plugin in plugins:
            if not plugin.active:
                pyblish.logic.log.debug("%s was inactive, skipping.." % plugin)
                continue

            self.state["nextOrder"] = plugin.order

            message = self.test(**self.state)
            if message:
                raise pyblish.logic.StopIteration("Stopped due to %s" % message)

            instances = pyblish.logic.instances_by_plugin(self.context, plugin)
            if collect:
                output.append([plugin, None])
            elif plugin.__instanceEnabled__:
                for instance in instances:
                    if instance.data.get("publish") is False:
                        pyblish.logic.log.debug("%s was inactive, skipping.." % instance)
                        continue

                    output.append([plugin, instance])

            else:
                output.append([plugin, None])
        return output

    def collect(self):
        """Yield next plug-in and instance to process.

        Arguments:
            plugins (list): Plug-ins to process
            context (pyblish.api.Context): Context to process

        """
        try:
            for pair in self._plugin_collect(self.plugins[self.PART_COLLECT], True):
                plug, instance = pair
                if not plug.active:
                    continue

                self.about_to_process.emit(*pair)

                self.processing["nextOrder"] = plug.order

                if self.test(**self.processing):
                    raise StopIteration("Stopped due to %s" % test(
                        **self.processing))

                result = self._process(*pair)

                if result["error"] is not None:
                    self.current_error = result["error"]

                self.was_processed.emit(result)

        except Exception as e:
            stack = traceback.format_exc(e)
            util.u_print(u"An unexpected error occurred:\n %s" % stack)
        finally:
            self.was_reset.emit()
            self.was_finished.emit()
            self.load_plugins()

    def validate(self):
        """Yield next plug-in and instance to process.

        Arguments:
            plugins (list): Plug-ins to process
            context (pyblish.api.Context): Context to process

        """

        try:
            for pair in self._plugin_collect(self.plugins[self.PART_VALIDATE]):
                plug, instance = pair
                if not plug.active:
                    continue
                try:
                    self.about_to_process.emit(plug, instance)
                    if not instance.data.get("publish"):
                        continue

                    self.processing["nextOrder"] = plug.order

                    if self.test(**self.processing):
                        raise StopIteration("Stopped due to %s" % test(
                            **self.processing))


                    result = self._process(*pair)
                    if result["error"] is not None:
                        self.current_error = result["error"]

                    self.was_processed.emit(result)

                except Exception as e:
                    stack = traceback.format_exc(e)
                    util.u_print(u"An unexpected error occurred:\n %s" % error)
            self.validated = True
        except Exception as e:
            traceback.print_tb(e.__traceback__)
        finally:
            self.on_validated()
            self.was_finished.emit()

    def publish(self):
        if not self.validated:
            self.validate()
        if self.current_error:
            return

        publish_plugins = []
        publish_plugins.extend(self.plugins[self.PART_EXTRACT])
        publish_plugins.extend(self.plugins[self.PART_CONFORM])
        try:
            for pair in self._plugin_collect(publish_plugins):
                plug, instance = pair
                if not plug.active:
                    continue
                try:
                    self.about_to_process.emit(plug, instance)
                    if not instance.data.get("publish"):
                        continue

                    self.processing["nextOrder"] = plug.order

                    if self.test(**self.processing):
                        raise StopIteration("Stopped due to %s" % test(
                            **self.processing))


                    result = self._process(*pair)
                    if result["error"] is not None:
                        self.current_error = result["error"]

                    self.was_processed.emit(result)

                except Exception as e:
                    error = traceback.format_tb(e.__traceback__)
                    util.u_print(u"An unexpected error occurred:\n %s" % error)
        except Exception as e:
            traceback.print_tb(e.__traceback__)
        finally:
            self.on_published()
            self.was_finished.emit()

    def cleanup(self):
        """Forcefully delete objects from memory

        In an ideal world, this shouldn't be necessary. Garbage
        collection guarantees that anything without reference
        is automatically removed.

        However, because this application is designed to be run
        multiple times from the same interpreter process, extra
        case must be taken to ensure there are no memory leaks.

        Explicitly deleting objects shines a light on where objects
        may still be referenced in the form of an error. No errors
        means this was uneccesary, but that's ok.

        """

        for instance in self.context:
            del(instance)

        for plugin in self.plugins:
            del(plugin)
