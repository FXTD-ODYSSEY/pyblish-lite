"""Main Window

States:
    These are all possible states and their transitions.


      reset
        '
        '
        '
     ___v__
    |      |       reset
    | Idle |--------------------.
    |      |<-------------------'
    |      |
    |      |                   _____________
    |      |     validate     |             |    reset     # TODO
    |      |----------------->| In-progress |-----------.
    |      |                  |_____________|           '
    |      |<-------------------------------------------'
    |      |
    |      |                   _____________
    |      |      publish     |             |
    |      |----------------->| In-progress |---.
    |      |                  |_____________|   '
    |      |<-----------------------------------'
    |______|


Todo:
    There are notes spread throughout this project with the syntax:

    - TODO(username)

    The `username` is a quick and dirty indicator of who made the note
    and is by no means exclusive to that person in terms of seeing it
    done. Feel free to do, or make your own TODO's as you code. Just
    make sure the description is sufficient for anyone reading it for
    the first time to understand how to actually to it!

"""
from functools import partial

from . import delegate, model, settings, util, view
from .awesome import tags as awesome

from .vendor.Qt import QtCore, QtGui, QtWidgets
from .constants import PluginStates, InstanceStates, Roles


class Window(QtWidgets.QDialog):
    def __init__(self, controller, parent=None):
        super(Window, self).__init__(parent=parent)
        icon = QtGui.QIcon(util.get_asset("img", "logo-extrasmall.png"))
        if parent is None:
            on_top_flag = QtCore.Qt.WindowStaysOnTopHint
        else:
            on_top_flag = QtCore.Qt.Dialog

        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
            | on_top_flag
        )
        self.setWindowIcon(icon)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.controller = controller

        main_widget = QtWidgets.QWidget(self)

        """General layout
         __________________       _____________________
        |                  |     |       |       |     |
        |      Header      | --> | Tab   | Tab   | Tab |
        |__________________|     |_______|_______|_____|
        |                  |      _____________________
        |                  |     |                     |
        |                  |     |                     |
        |       Body       |     |                     |
        |                  | --> |        Page         |
        |                  |     |                     |
        |                  |     |_____________________|
        |__________________|      _____________________
        |                  |     |           |         |
        |      Footer      |     | Status    | Buttons |
        |__________________|     |___________|_________|

        """

        header_widget = QtWidgets.QWidget(parent=main_widget)

        header_tab_widget = QtWidgets.QWidget(header_widget)
        header_tab_artist = QtWidgets.QRadioButton(header_tab_widget)
        header_tab_overview = QtWidgets.QRadioButton(header_tab_widget)
        header_tab_terminal = QtWidgets.QRadioButton(header_tab_widget)
        header_spacer = QtWidgets.QWidget(header_tab_widget)

        header_aditional_btns = QtWidgets.QWidget(header_tab_widget)

        aditional_btns_layout = QtWidgets.QHBoxLayout(header_aditional_btns)

        presets_button = view.ButtonWithMenu(awesome["filter"])
        presets_button.setEnabled(False)
        aditional_btns_layout.addWidget(presets_button)

        layout_tab = QtWidgets.QHBoxLayout(header_tab_widget)
        layout_tab.setContentsMargins(0, 0, 0, 0)
        layout_tab.setSpacing(0)
        layout_tab.addWidget(header_tab_artist, 0)
        layout_tab.addWidget(header_tab_overview, 0)
        layout_tab.addWidget(header_tab_terminal, 0)
        # Compress items to the left
        layout_tab.addWidget(header_spacer, 1)
        layout_tab.addWidget(header_aditional_btns, 1)

        layout = QtWidgets.QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header_tab_widget)

        header_widget.setLayout(layout)

        """Artist Page
         __________________
        |                  |
        | | ------------   |
        | | -----          |
        |                  |
        | | --------       |
        | | -------        |
        |                  |
        |__________________|

        """
        instance_model = model.InstanceModel(controller)

        artist_page = QtWidgets.QWidget()

        artist_view = view.Item()
        artist_view.show_perspective.connect(self.toggle_perspective_widget)
        artist_view.setModel(instance_model)

        artist_delegate = delegate.Artist()
        artist_view.setItemDelegate(artist_delegate)

        layout = QtWidgets.QVBoxLayout(artist_page)
        layout.addWidget(artist_view)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        artist_page.setLayout(layout)

        """Overview Page
         ___________________
        |                  |
        | o ----- o----    |
        | o ----  o---     |
        | o ----  o----    |
        | o ----  o------  |
        |                  |
        |__________________|

        """

        # TODO add parent
        overview_page = QtWidgets.QWidget()

        overview_instance_view = view.OverviewView(parent=overview_page)
        overview_instance_delegate = delegate.InstanceDelegate(
            parent=overview_instance_view
        )
        overview_instance_view.setItemDelegate(overview_instance_delegate)
        overview_instance_view.setModel(instance_model)

        overview_plugin_view = view.OverviewView(parent=overview_page)
        overview_plugin_delegate = delegate.PluginDelegate(
            parent=overview_plugin_view
        )
        overview_plugin_view.setItemDelegate(overview_plugin_delegate)
        plugin_model = model.PluginModel(controller)
        overview_plugin_view.setModel(plugin_model)

        layout = QtWidgets.QHBoxLayout(overview_page)
        layout.addWidget(overview_instance_view, 1)
        layout.addWidget(overview_plugin_view, 1)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        overview_page.setLayout(layout)

        """Terminal

         __________________
        |                  |
        |  \               |
        |   \              |
        |   /              |
        |  /  ______       |
        |                  |
        |__________________|

        """

        terminal_container = QtWidgets.QWidget()

        terminal_delegate = delegate.LogsAndDetails()
        terminal_view = view.TerminalView()
        terminal_view.setItemDelegate(terminal_delegate)

        terminal_model = model.Terminal()

        terminal_proxy = model.TerminalProxy()
        terminal_proxy.setSourceModel(terminal_model)

        terminal_view.setModel(terminal_proxy)

        layout = QtWidgets.QVBoxLayout(terminal_container)
        layout.addWidget(terminal_view)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        terminal_container.setLayout(layout)

        terminal_page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(terminal_page)
        layout.addWidget(terminal_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add some room between window borders and contents
        body_widget = QtWidgets.QWidget(main_widget)
        layout = QtWidgets.QHBoxLayout(body_widget)
        layout.setContentsMargins(5, 5, 5, 1)
        layout.addWidget(artist_page)
        layout.addWidget(overview_page)
        layout.addWidget(terminal_page)

        """Comment Box
         ____________________________ ______________
        |> My comment                | intent [ v ] |
        |                            |              |
        |____________________________|______________|

        """

        comment_box = view.CommentBox("Comment...", self)

        intent_box = QtWidgets.QComboBox()

        intent_model = model.IntentModel()
        intent_box.setModel(intent_model)
        intent_box.currentIndexChanged.connect(self.on_intent_changed)

        comment_intent_widget = QtWidgets.QWidget()
        comment_intent_layout = QtWidgets.QHBoxLayout(comment_intent_widget)
        comment_intent_layout.setContentsMargins(0, 0, 0, 0)
        comment_intent_layout.setSpacing(5)
        comment_intent_layout.addWidget(comment_box)
        comment_intent_layout.addWidget(intent_box)

        """Footer
         ______________________
        |             ___  ___ |
        |            | o || > ||
        |            |___||___||
        |______________________|

        """

        footer_widget = QtWidgets.QWidget(main_widget)

        footer_info = QtWidgets.QLabel(footer_widget)
        footer_spacer = QtWidgets.QWidget(footer_widget)
        footer_button_reset = QtWidgets.QPushButton(
            awesome["refresh"], footer_widget
        )
        footer_button_validate = QtWidgets.QPushButton(
            awesome["flask"], footer_widget
        )
        footer_button_play = QtWidgets.QPushButton(
            awesome["play"], footer_widget
        )
        footer_button_stop = QtWidgets.QPushButton(
            awesome["stop"], footer_widget
        )

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(footer_info, 0)
        layout.addWidget(footer_spacer, 1)
        layout.addWidget(footer_button_stop, 0)
        layout.addWidget(footer_button_reset, 0)
        layout.addWidget(footer_button_validate, 0)
        layout.addWidget(footer_button_play, 0)

        footer_layout = QtWidgets.QVBoxLayout(footer_widget)
        footer_layout.addWidget(comment_intent_widget)
        footer_layout.addLayout(layout)

        footer_widget.setProperty("success", -1)

        # Placeholder for when GUI is closing
        # TODO(marcus): Fade to black and the the user about what's happening
        closing_placeholder = QtWidgets.QWidget(main_widget)
        closing_placeholder.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        closing_placeholder.hide()

        self.last_persp_index = None
        self.perspective_widget = view.PerspectiveWidget(self)
        self.perspective_widget.hide()

        # Main layout
        layout = QtWidgets.QVBoxLayout(main_widget)
        layout.addWidget(header_widget, 0)
        layout.addWidget(body_widget, 3)
        layout.addWidget(self.perspective_widget, 3)
        layout.addWidget(closing_placeholder, 1)
        layout.addWidget(footer_widget, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        main_widget.setLayout(layout)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(main_widget)

        """Animation
           ___
          /   \
         |     |            ___
          \___/            /   \
                   ___    |     |
                  /   \    \___/
                 |     |
                  \___/

        """

        # Display info
        info_effect = QtWidgets.QGraphicsOpacityEffect(footer_info)
        footer_info.setGraphicsEffect(info_effect)

        on = QtCore.QPropertyAnimation(info_effect, b"opacity")
        on.setDuration(0)
        on.setStartValue(0)
        on.setEndValue(1)

        off = QtCore.QPropertyAnimation(info_effect, b"opacity")
        off.setDuration(0)
        off.setStartValue(1)
        off.setEndValue(0)

        fade = QtCore.QPropertyAnimation(info_effect, b"opacity")
        fade.setDuration(500)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)

        timeline = QtCore.QSequentialAnimationGroup()
        timeline.addAnimation(on)
        timeline.addPause(50)
        timeline.addAnimation(off)
        timeline.addPause(50)
        timeline.addAnimation(on)
        timeline.addPause(2000)
        timeline.addAnimation(fade)

        info_animation = timeline

        """Setup

        Widgets are referred to in CSS via their object-name. We
        use the same mechanism internally to refer to objects; so rather
        than storing widgets as self.my_widget, it is referred to as:

        >>> my_widget = self.findChild(QtWidgets.QWidget, "MyWidget")

        This way there is only ever a single method of referring to any widget.

              ___
             |   |
          /\/     \/\
         /     _     \
         \    / \    /
          |   | |   |
         /    \_/    \
         \           /
          \/\     /\/
             |___|

        """

        names = {
            # Main
            "Header": header_widget,
            "Body": body_widget,
            "Footer": footer_widget,

            # Pages
            "Artist": artist_page,
            "Overview": overview_page,
            "Terminal": terminal_page,

            # Tabs
            "ArtistTab": header_tab_artist,
            "OverviewTab": header_tab_overview,
            "TerminalTab": header_tab_terminal,

            # Buttons
            "Play": footer_button_play,
            "Validate": footer_button_validate,
            "Reset": footer_button_reset,
            "Stop": footer_button_stop,

            # Misc
            "HeaderSpacer": header_spacer,
            "FooterSpacer": footer_spacer,
            "FooterInfo": footer_info,
            "CommentIntentWidget": comment_intent_widget,
            "CommentBox": comment_box,
            "CommentPlaceholder": comment_box.placeholder,
            "ClosingPlaceholder": closing_placeholder,
            "IntentBox": intent_box
        }

        for name, _widget in names.items():
            _widget.setObjectName(name)

        # Enable CSS on plain QWidget objects
        for _widget in (
            header_widget,
            body_widget,
            artist_page,
            comment_box,
            overview_page,
            terminal_page,
            footer_widget,
            footer_button_play,
            footer_button_validate,
            footer_button_stop,
            footer_button_reset,
            footer_spacer,
            closing_placeholder
        ):
            _widget.setAttribute(QtCore.Qt.WA_StyledBackground)

        """Signals
         ________     ________
        |________|-->|________|
                         |
                         |
                      ___v____
                     |________|

        """

        header_tab_artist.toggled.connect(
            lambda: self.on_tab_changed("artist")
        )
        header_tab_overview.toggled.connect(
            lambda: self.on_tab_changed("overview")
        )
        header_tab_terminal.toggled.connect(
            lambda: self.on_tab_changed("terminal")
        )

        overview_instance_view.show_perspective.connect(
            self.toggle_perspective_widget
        )
        overview_plugin_view.show_perspective.connect(
            self.toggle_perspective_widget
        )

        controller.passed_group.connect(self.on_passed_group)
        controller.was_acted.connect(self.on_was_acted)
        controller.was_finished.connect(self.on_was_finished)
        controller.switch_toggleability.connect(self.change_toggleability)
        # Discovery happens synchronously during reset, that's
        # why it's important that this connection is triggered
        # right away.
        controller.was_reset.connect(
            self.on_was_reset,
            QtCore.Qt.DirectConnection
        )

        # This is called synchronously on each process
        controller.was_processed.connect(
            self.on_was_processed,
            QtCore.Qt.DirectConnection
        )

        # NOTE: Listeners to this signal are run in the main thread
        controller.about_to_process.connect(
            self.on_about_to_process,
            QtCore.Qt.DirectConnection
        )

        artist_view.toggled.connect(self.on_item_toggled)
        overview_instance_view.toggled.connect(self.on_item_toggled)
        overview_plugin_view.toggled.connect(self.on_item_toggled)

        footer_button_stop.clicked.connect(self.on_stop_clicked)
        footer_button_reset.clicked.connect(self.on_reset_clicked)
        footer_button_validate.clicked.connect(self.on_validate_clicked)
        footer_button_play.clicked.connect(self.on_play_clicked)

        comment_box.textChanged.connect(self.on_comment_entered)
        comment_box.returnPressed.connect(self.on_play_clicked)
        overview_plugin_view.customContextMenuRequested.connect(
            self.on_plugin_action_menu_requested
        )

        self.main_widget = main_widget

        self.header_widget = header_widget
        self.body_widget = body_widget

        self.footer_button_reset = footer_button_reset
        self.footer_button_validate = footer_button_validate
        self.footer_button_play = footer_button_play
        self.footer_button_stop = footer_button_stop

        self.overview_instance_view = overview_instance_view
        self.overview_plugin_view = overview_plugin_view
        self.plugin_model = plugin_model
        self.instance_model = instance_model

        self.data = {
            "footer": footer_widget,
            "views": {
                "artist": artist_view,
                "terminal": terminal_view,
            },
            "proxies": {
                "terminal": terminal_proxy
            },
            "models": {
                "terminal": terminal_model,
                "intent_model": intent_model
            },
            "tabs": {
                "artist": header_tab_artist,
                "overview": header_tab_overview,
                "terminal": header_tab_terminal,
                "current": "artist"
            },
            "pages": {
                "artist": artist_page,
                "overview": overview_page,
                "terminal": terminal_page,
            },
            "comment_intent": {
                "comment_intent": comment_intent_widget,
                "comment": comment_box,
                "intent": intent_box
            },
            "aditional_btns": {
                "presets_button": presets_button
            },
            "animation": {
                "display_info": info_animation,
            },
            "state": {
                "is_closing": False,
            }
        }

        self.data["tabs"][settings.InitialTab].setChecked(True)

    # -------------------------------------------------------------------------
    #
    # Event handlers
    #
    # -------------------------------------------------------------------------
    def set_presets(self, key):
        plugin_settings = self.controller.possible_presets.get(key)
        if not plugin_settings:
            return

        for plugin_item in self.plugin_model.plugin_items.values():
            if not plugin_item.plugin.optional:
                continue

            value = plugin_settings.get(
                plugin_item.plugin.__name__,
                # if plugin is not in presets then set default value
                self.controller.optional_default.get(
                    plugin_item.plugin.__name__
                )
            )
            if value is None:
                continue

            plugin_item.setData(value, QtCore.Qt.CheckStateRole)

    def toggle_perspective_widget(self, index=None):
        show = False
        self.last_persp_index = None
        if index:
            show = True
            self.last_persp_index = index
            self.perspective_widget.set_context(index)

        self.body_widget.setVisible(not show)
        self.header_widget.setVisible(not show)

        self.perspective_widget.setVisible(show)

    def change_toggleability(self, enable_value):
        for plugin_item in self.plugin_model.plugin_items.values():
            plugin_item.setData(enable_value, Roles.IsEnabledRole)

    def on_item_toggled(self, index, state=None):
        """An item is requesting to be toggled"""
        if not index.data(Roles.IsOptionalRole):
            return self.info("This item is mandatory")

        if self.controller.collect_state != 1:
            return self.info("Cannot toggle")

        if state is None:
            state = not index.data(QtCore.Qt.CheckStateRole)

        item = index.data(Roles.ItemRole)
        item.setData(state, QtCore.Qt.CheckStateRole)

    def on_tab_changed(self, target):
        for page in self.data["pages"].values():
            page.hide()

        page = self.data["pages"][target]

        comment_intent = self.data["comment_intent"]["comment_intent"]
        if target == "terminal":
            comment_intent.setVisible(False)
        else:
            comment_intent.setVisible(True)

        page.show()

        self.data["tabs"]["current"] = target

    def on_validate_clicked(self):
        comment_box = self.data["comment_intent"]["comment"]
        intent_box = self.data["comment_intent"]["intent"]

        comment_box.setEnabled(False)
        intent_box.setEnabled(False)

        self.validate()

    def on_play_clicked(self):
        comment_box = self.data["comment_intent"]["comment"]
        intent_box = self.data["comment_intent"]["intent"]

        comment_box.setEnabled(False)
        intent_box.setEnabled(False)

        self.publish()

    def on_reset_clicked(self):
        self.reset()

    def on_stop_clicked(self):
        self.info("Stopping..")
        self.controller.stop()

        # TODO checks
        self.footer_button_reset.setEnabled(True)
        self.footer_button_play.setEnabled(False)
        self.footer_button_stop.setEnabled(False)

    def on_comment_entered(self):
        """The user has typed a comment"""
        text_edit = self.data["comment_intent"]["comment"]
        # Store within context
        self.controller.context.data["comment"] = text_edit.text()

    def on_intent_changed(self):
        intent_box = self.data["comment_intent"]["intent"]
        idx = intent_box.model().index(intent_box.currentIndex(), 0)
        intent_value = intent_box.model().data(idx, Roles.IntentItemValue)
        intent_label = intent_box.model().data(idx, QtCore.Qt.DisplayRole)

        # TODO move to play
        if self.controller.context:
            self.controller.context.data["intent"] = {
                "value": intent_value,
                "label": intent_label
            }

    def on_about_to_process(self, plugin, instance):
        """Reflect currently running pair in GUI"""
        if instance is None:
            instance_id = self.controller.context.id
        else:
            instance_id = instance.id

        instance_item = self.instance_model.instance_items[instance_id]
        instance_item.setData(
            {InstanceStates.InProgress: True},
            Roles.PublishFlagsRole
        )

        plugin_item = self.plugin_model.plugin_items[plugin._id]
        plugin_item.setData(
            {PluginStates.InProgress: True},
            Roles.PublishFlagsRole
        )

        self.info("{} {}".format(
            self.tr("Processing"), plugin_item.data(QtCore.Qt.DisplayRole)
        ))

    def on_plugin_action_menu_requested(self, pos):
        """The user right-clicked on a plug-in
         __________
        |          |
        | Action 1 |
        | Action 2 |
        | Action 3 |
        |          |
        |__________|

        """

        index = self.overview_plugin_view.indexAt(pos)
        actions = index.data(Roles.PluginValidActionsRole)

        if not actions:
            return

        menu = QtWidgets.QMenu(self)
        plugin = index.data(Roles.ObjectRole)
        print("plugin is: %s" % plugin)

        for action in actions:
            qaction = QtWidgets.QAction(action.label or action.__name__, self)
            qaction.triggered.connect(partial(self.act, plugin, action))
            menu.addAction(qaction)

        menu.popup(self.overview_plugin_view.viewport().mapToGlobal(pos))

    def update_compatibility(self):
        self.plugin_model.update_compatibility(
            self.controller.context,
            self.instance_model.instance_items.values()
        )

        right_view_model = self.overview_plugin_view.model()
        # for child in right_view_model.root.children():
        #     child_idx = right_view_model.createIndex(child.row(), 0, child)
        #     self.overview_plugin_view.expand(child_idx)
        #     any_failed = False
        #     all_succeeded = True
        #     for plugin_item in child.children():
        #         if plugin_item.data(model.IsOptional):
        #             if not plugin_item.data(model.IsChecked):
        #                 continue
        #         if plugin_item.data(model.HasFailed):
        #             any_failed = True
        #             break
        #         if not plugin_item.data(model.HasSucceeded):
        #             all_succeeded = False
        #             break
        #
        #     if all_succeeded and not any_failed:
        #         self.overview_plugin_view.collapse(child_idx)

    def on_was_reset(self):
        # Append context object to instances model
        self.instance_model.append(self.controller.context)

        for plugin in self.controller.plugins:
            self.plugin_model.append(plugin)

        self.overview_instance_view.expandAll()
        self.overview_plugin_view.expandAll()

        self.footer_button_play.setEnabled(True)
        self.footer_button_validate.setEnabled(True)
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

        aditional_btns = self.data["aditional_btns"]
        aditional_btns["presets_button"].clearMenu()
        if self.controller.possible_presets:
            aditional_btns["presets_button"].setEnabled(True)
            for key in self.controller.possible_presets:
                aditional_btns["presets_button"].addItem(
                    key, partial(self.set_presets, key)
                )

        self.instance_model.restore_checkstates()
        self.plugin_model.restore_checkstates()

        # Append placeholder comment from Context
        # This allows users to inject a comment from elsewhere,
        # or to perhaps provide a placeholder comment/template
        # for artists to fill in.
        comment = self.controller.context.data.get("comment")
        comment_box = self.data["comment_intent"]["comment"]
        comment_box.setText(comment or None)
        comment_box.setEnabled(True)

        intent_box = self.data["comment_intent"]["intent"]
        intent_model = intent_box.model()
        if intent_model.has_items:
            self.on_intent_changed()
        intent_box.setEnabled(True)

        # Refresh tab
        self.on_tab_changed(self.data["tabs"]["current"])
        self.update_compatibility()

        intent_box.setFocus()
        self.footer_button_play.setFocus()

    def on_passed_group(self):
        self.overview_instance_view.expandAll()

        failed = False
        for plugin_item in self.plugin_model.plugin_items.values():
            # TODO check only plugins from the group
            publish_states = plugin_item.data(Roles.PublishFlagsRole)
            if not failed and publish_states & PluginStates.HasError:
                failed = True
                break

        # TODO collapse group is success
        # if not failed:
        #     self.overview_plugin_view.collapse()

        self.footer_button_play.setEnabled(not failed)
        self.footer_button_validate.setEnabled(
            not failed and not self.controller.validated
        )
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

    def on_was_finished(self):
        self.overview_instance_view.expandAll()

        self.footer_button_play.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

        success_val = 0
        if self.controller.errored:
            self.info(self.tr("Stopped due to error(s), see Terminal."))
            comment_box = self.data["comment_intent"]["comment"]
            comment_box.setEnabled(False)
            intent_box = self.data["comment_intent"]["intent"]
            intent_box.setEnabled(False)

        else:
            success_val = 1
            self.info(self.tr("Finished successfully!"))

        self.data["footer"].setProperty("success", success_val)
        self.data["footer"].style().polish(self.data["footer"])

        self.update_compatibility()

    def on_was_processed(self, result):
        for instance in self.controller.context:
            if instance.id not in self.instance_model.instance_items:
                self.instance_model.append(instance)

        error = result.get("error")
        if error:
            records = result.get("records") or []
            fname, line_no, func, exc = error.traceback

            records.append({
                "label": str(error),
                "type": "error",
                "filename": str(fname),
                "lineno": str(line_no),
                "func": str(func),
                "traceback": error.formatted_traceback,
            })

            result["records"] = records

            # Toggle from artist to overview tab on error
            if self.data["tabs"]["artist"].isChecked():
                self.data["tabs"]["overview"].toggle()

        self.plugin_model.update_with_result(result)
        self.instance_model.update_with_result(result)

        models = self.data["models"]
        models["terminal"].update_with_result(result)
        self.data["proxies"]["terminal"].rebuild()

        self.update_compatibility()

        if self.last_persp_index:
            self.perspective_widget.set_context(self.last_persp_index)

    def on_was_acted(self, result):
        # TODO implement
        self.overview_instance_view.expandAll()

        self.footer_button_reset.setEnabled(True)
        self.footer_button_stop.setEnabled(False)

        # Update action with result
        index = self.plugin_model.items.index(result["plugin"])
        index = self.plugin_model.createIndex(index, 0)

        self.plugin_model.setData(index, not result["success"], Roles.ActionFailed)
        self.plugin_model.setData(index, False, Roles.InProgress)

        models = self.data["models"]

        error = result.get('error')
        if error:
            records = result.get('records') or []
            fname, line_no, func, exc = error.traceback

            records.append({
                'label': str(error),
                'type': 'error',
                'filename': str(fname),
                'lineno': str(line_no),
                'func': str(func),
                'traceback': error.formatted_traceback
            })

            result['records'] = records

        self.plugin_model.update_with_result(result)
        models["instances"].update_with_result(result)
        models["terminal"].update_with_result(result)
    # -------------------------------------------------------------------------
    #
    # Functions
    #
    # -------------------------------------------------------------------------

    def reset(self):
        """Prepare GUI for reset"""
        self.info(self.tr("About to reset.."))

        self.data["aditional_btns"]["presets_button"].setEnabled(False)
        self.data["footer"].setProperty("success", -1)
        self.data["footer"].style().polish(self.data["footer"])

        self.instance_model.store_checkstates()
        self.plugin_model.store_checkstates()

        # Reset current ids to secure no previous instances get mixed in.
        models = self.data["models"]
        for model in models.values():
            model.reset()
        self.instance_model.reset()
        self.plugin_model.reset()

        self.footer_button_stop.setEnabled(False)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        intent_box = self.data["comment_intent"]["intent"]
        intent_model = intent_box.model()
        intent_box.setVisible(intent_model.has_items)
        if intent_model.has_items:
            intent_box.setCurrentIndex(intent_model.default_index)

        # Launch controller reset
        util.defer(500, self.controller.reset)

    def validate(self):
        self.info(self.tr("Preparing validate.."))
        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        util.defer(5, self.controller.validate)

    def publish(self):
        self.info(self.tr("Preparing publish.."))

        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        util.defer(5, self.controller.publish)

    def act(self, plugin, action):
        self.info("%s %s.." % (self.tr("Preparing"), action))

        self.footer_button_stop.setEnabled(True)
        self.footer_button_reset.setEnabled(False)
        self.footer_button_validate.setEnabled(False)
        self.footer_button_play.setEnabled(False)

        self.controller.is_running = True

        # Cause view to update, but it won't visually
        # happen until Qt is given time to idle..
        plugin_item = self.plugin_model.plugin_items[plugin._id]

        for key, value in {
            Roles.ActionIdle: False,
            Roles.ActionFailed: False,
            Roles.InProgress: True
        }.items():
            plugin_item.setData(value, key)

        # Give Qt time to draw
        util.defer(100, lambda: self.controller.act(
            plugin_item.plugin, action
        ))

        self.info(self.tr("Action prepared."))

    def closeEvent(self, event):
        """Perform post-flight checks before closing

        Make sure processing of any kind is wrapped up before closing

        """

        # Make it snappy, but take care to clean it all up.
        # TODO(marcus): Enable GUI to return on problem, such
        # as asking whether or not the user really wants to quit
        # given there are things currently running.
        self.hide()

        if self.data["state"]["is_closing"]:

            # Explicitly clear potentially referenced data
            self.info(self.tr("Cleaning up models.."))
            for view in self.data["views"].values():
                view.model().deleteLater()
                view.setModel(None)

            self.info(self.tr("Cleaning up terminal.."))
            for item in self.data["models"]["terminal"].items:
                del(item)

            self.info(self.tr("Cleaning up controller.."))
            self.controller.cleanup()

            self.info(self.tr("All clean!"))
            self.info(self.tr("Good bye"))
            return super(Window, self).closeEvent(event)

        self.info(self.tr("Closing.."))

        def on_problem():
            self.heads_up("Warning", "Had trouble closing down. "
                          "Please tell someone and try again.")
            self.show()

        if self.controller.is_running:
            self.info(self.tr("..as soon as processing is finished.."))
            self.controller.stop()
            self.finished.connect(self.close)
            util.defer(2000, on_problem)
            return event.ignore()

        self.data["state"]["is_closing"] = True

        util.defer(200, self.close)
        return event.ignore()

    def reject(self):
        """Handle ESC key"""

        if self.controller.is_running:
            self.info(self.tr("Stopping.."))
            self.controller.stop()

    # -------------------------------------------------------------------------
    #
    # Feedback
    #
    # -------------------------------------------------------------------------

    def info(self, message):
        """Print user-facing information

        Arguments:
            message (str): Text message for the user

        """

        info = self.findChild(QtWidgets.QLabel, "FooterInfo")
        info.setText(message)

        # Include message in terminal
        self.data["models"]["terminal"].append({
            "label": message,
            "type": "info"
        })

        animation = self.data["animation"]["display_info"]
        animation.stop()
        animation.start()

        # TODO(marcus): Should this be configurable? Do we want
        # the shell to fill up with these messages?
        util.u_print(message)

    def warning(self, message):
        """Block processing and print warning until user hits "Continue"

        Arguments:
            message (str): Message to display

        """

        # TODO(marcus): Implement this.
        self.info(message)

    def heads_up(self, title, message, command=None):
        """Provide a front-and-center message with optional command

        Arguments:
            title (str): Bold and short message
            message (str): Extended message
            command (optional, callable): Function is provided as a button

        """

        # TODO(marcus): Implement this.
        self.info(message)
