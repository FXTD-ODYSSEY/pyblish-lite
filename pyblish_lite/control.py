"""The Controller in a Model/View/Controller-based application
The graphical components of Pyblish Lite use this object to perform
publishing. It communicates via the Qt Signals/Slots mechanism
and has no direct connection to any graphics. This is important,
because this is how unittests are able to run without requiring
an active window manager; such as via Travis-CI.
"""
import os
import sys

from .vendor.Qt import QtCore

import pyblish.api
import pyblish.util
import pyblish.logic
import pyblish.lib
import pyblish.version

from . import util
try:
    from pypeapp.config import get_presets
except Exception:
    def get_presets(): return {}


class Controller(QtCore.QObject):

    # Emitted when the GUI is about to start processing;
    # e.g. resetting, validating or publishing.
    about_to_process = QtCore.Signal(object, object)

    # ??? Emitted for each process
    was_processed = QtCore.Signal(dict)

    # Emmited when reset
    # - all data are reset (plugins, processing, pari yielder, etc.)
    was_reset = QtCore.Signal()

    # Emmited when previous group changed
    passed_group = QtCore.Signal()

    # ??? Probably action finished
    was_acted = QtCore.Signal(dict)

    # Emitted when processing has stopped
    was_stopped = QtCore.Signal()

    # Emitted when processing has finished
    was_finished = QtCore.Signal()

    # store OrderGroups - now it is a singleton
    order_groups = util.OrderGroups

    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        self.context = None
        self.plugins = {}
        self.optional_default = {}

    def reset_variables(self):
        # Data internal to the GUI itself
        self.is_running = False
        self.stopped = False
        self.errored = False

        # Active producer of pairs
        self.pair_generator = None
        # Active pair
        self.current_pair = None

        # Orders which changes GUI
        # - passing collectors order disables plugin/instance toggle
        self.collectors_order = None
        self.collected = False

        # - passing validators order disables validate button and gives ability
        #   to know when to stop on validate button press
        self.validators_order = None
        self.validated = False

        # Get collectors and validators order
        self.order_groups.reset()
        plugin_groups = self.order_groups.groups()
        plugin_groups_keys = list(plugin_groups.keys())
        self.collectors_order = plugin_groups_keys[0]
        self.validators_order = self.order_groups.validation_order()
        next_order = None
        if len(plugin_groups_keys) > 1:
            next_order = plugin_groups_keys[1]

        # This is used to track whether or not to continue
        # processing when, for example, validation has failed.
        self.processing = {
            "stop_on_validation": False,
            # Used?
            "last_plugin_order": None,
            "current_order": self.collectors_order,
            "next_order": next_order,
            "nextOrder": None,
            "ordersWithError": set()
        }

    def presets_by_hosts(self):
        # Get global filters as base
        presets = get_presets().get("plugins", {})
        if not presets:
            return {}

        result = presets.get("global", {}).get("filter", {})
        hosts = pyblish.api.registered_hosts()
        for host in hosts:
            host_presets = presets.get(host, {}).get("filter")
            if not host_presets:
                continue

            for key, value in host_presets.items():
                if value is None:
                    if key in result:
                        result.pop(key)
                    continue

                result[key] = value

        return result

    def reset_context(self):
        self.context = None

        new_context = pyblish.api.Context()

        new_context._has_failed = False
        new_context._has_succeeded = False
        new_context._has_processed = False
        new_context._has_warning = False
        new_context._is_processing = False
        new_context._is_idle = False
        new_context._type = "context"
        new_context.optional = False

        new_context.data["publish"] = True
        new_context.data["label"] = "Context"
        new_context.data["name"] = "context"

        new_context.data["host"] = reversed(pyblish.api.registered_hosts())
        new_context.data["port"] = int(
            os.environ.get("PYBLISH_CLIENT_PORT", -1)
        )
        new_context.data["connectTime"] = pyblish.lib.time(),
        new_context.data["pyblishVersion"] = pyblish.version,
        new_context.data["pythonVersion"] = sys.version

        new_context.data["icon"] = "book"

        new_context.families = ("__context__",)

        self.context = new_context

    def reset(self):
        """Discover plug-ins and run collection."""

        self.reset_context()
        self.reset_variables()

        self.possible_presets = self.presets_by_hosts()

        # Load plugins and set pair generator
        self.load_plugins()
        self.pair_generator = self._pair_yielder(self.plugins)

        self.was_reset.emit()

        # Process collectors load rest of plugins with collected instances
        self.collect()

    def load_plugins(self):
        self.test = pyblish.logic.registered_test()
        self.optional_default = {}

        plugins = pyblish.api.discover()

        targets = pyblish.logic.registered_targets() or ["default"]
        self.plugins = pyblish.logic.plugins_by_targets(plugins, targets)

    def on_finished(self):
        self.was_finished.emit()

    def stop(self):
        self.stopped = True

    def act(self, plugin, action):
        def on_next():
            result = pyblish.plugin.process(
                plugin, self.context, None, action.id
            )
            self.was_acted.emit(result)

        util.defer(100, on_next)

    def emit_(self, signal, kwargs):
        pyblish.api.emit(signal, **kwargs)

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
            # Make note of the order at which the
            # potential error error occured.
            if result["error"] is not None:
                self.processing["ordersWithError"].add(plugin.order)

        except Exception as exc:
            raise Exception("Unknown error({}): {}".format(
                plugin.__name__, str(exc)
            ))

        return result

    def _pair_yielder(self, plugins):
        for plugin in plugins:
            if (
                self.processing["current_order"] is not None
                and plugin.order > self.processing["current_order"]
            ):
                new_next_order = None
                new_current_order = self.processing["next_order"]
                if new_current_order is not None:
                    current_next_order_found = False
                    for order in self.order_groups.groups().keys():
                        if current_next_order_found:
                            new_next_order = order
                            break

                        if order == new_current_order:
                            current_next_order_found = True

                self.processing["current_order"] = new_current_order
                self.processing["next_order"] = new_next_order
                print("***** passed group")
                self.passed_group.emit()

            if not self.collected and plugin.order > self.collectors_order:
                self.collected = True
                raise StopIteration("Collected")

            if not self.validated and plugin.order > self.validators_order:
                self.validated = True
                if self.processing["stop_on_validation"]:
                    raise StopIteration("Validated")

            # Stop if was stopped
            if self.stopped:
                raise StopIteration("Stopped")

            # check test if will stop
            self.processing["nextOrder"] = plugin.order
            message = self.test(**self.processing)
            if message:
                raise StopIteration(
                    "Stopped due to \"{}\"".format(message)
                )

            self.processing["last_plugin_order"] = plugin.order
            if not plugin.active:
                pyblish.logic.log.debug("%s was inactive, skipping.." % plugin)
                continue

            if plugin.__instanceEnabled__:
                instances = pyblish.logic.instances_by_plugin(
                    self.context, plugin
                )
                for instance in instances:
                    if instance.data.get("publish") is False:
                        pyblish.logic.log.debug(
                            "%s was inactive, skipping.." % instance
                        )
                        continue
                    yield plugin, instance
            else:
                families = util.collect_families_from_instances(
                    self.context, only_active=True
                )
                plugins = pyblish.logic.plugins_by_families(
                    [plugin], families
                )
                if not plugins:
                    continue
                yield plugin, None

    def iterate_and_process(self, on_finished=lambda: None):
        """ Iterating inserted plugins with current context.
        Collectors do not contain instances, they are None when collecting!
        This process don't stop on one
        """
        def on_next():
            try:
                if self.current_pair is None:
                    self.current_pair = next(self.pair_generator, (None, None))
                else:
                    self.current_pair = next(self.pair_generator)

            except StopIteration:
                self.is_running = False
                # All pairs were processed successfully!
                if self.stopped:
                    return
                return util.defer(500, on_finished)

            except Exception:
                # This is a bug
                exc_type, exc_msg, exc_tb = sys.exc_info()
                self.is_running = False
                self.current_pair = (None, None)
                return util.defer(
                    500, lambda: on_unexpected_error(error=exc_msg)
                )

            if self.current_pair == (None, None):
                return util.defer(100, on_finished)

            self.about_to_process.emit(*self.current_pair)
            util.defer(100, on_process)

        def on_process():
            try:
                print("*** on_process: begin {}".format(str(self.current_pair)))
                result = self._process(*self.current_pair)
                if result["error"] is not None:
                    self.current_error = result["error"]

                print("*** on_process: after _process")
                self.was_processed.emit(result)
                print("*** on_process: was_processed emit")

            except Exception:
                exc_type, exc_msg, exc_tb = sys.exc_info()
                # return
                return util.defer(
                    500, lambda: on_unexpected_error(error=exc_msg)
                )

            util.defer(10, on_next)
            print("*** on_process: after on_next")

        def on_unexpected_error(error):
            util.u_print(u"An unexpected error occurred:\n %s" % error)
            return util.defer(500, on_finished)

        self.is_running = True
        util.defer(10, on_next)

    def collect(self):
        """ Iterate and process Collect plugins
        - load_plugins method is launched again when finished
        """
        self.iterate_and_process()

    def validate(self):
        """ Process plugins to validations_order value."""
        self.processing["stop_on_validation"] = True
        self.iterate_and_process()

    def publish(self):
        """ Iterate and process all remaining plugins."""
        self.processing["stop_on_validation"] = False
        self.iterate_and_process(self.on_finished)

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
