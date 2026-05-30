import flask
import octoprint.plugin
from octoprint.events import Events


class LayerNotifyPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    def __init__(self):
        self._triggered = set()  # layers already fired this print

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings_defaults(self):
        # layers: list of {layer: int, command: str, enabled: bool}
        return dict(
            layers=[],
            sound_enabled=True,
            sound_type="triple",   # single | triple | alarm | rising
            sound_volume=0.5,      # 0.0 – 1.0
        )

    # ── Templates ─────────────────────────────────────────────────────────────

    def get_template_configs(self):
        return [
            dict(
                type="settings",
                template="layer_notify_settings.jinja2",
                custom_bindings=True,
            ),
            dict(
                type="tab",
                template="layer_notify_tab.jinja2",
                custom_bindings=True,
                name="Layer Notify",
            ),
        ]

    # ── Assets ────────────────────────────────────────────────────────────────

    def get_assets(self):
        return dict(js=["js/layer_notify.js"])

    # ── Events ────────────────────────────────────────────────────────────────

    def on_event(self, event, payload):
        if event in (Events.PRINT_STARTED, Events.PRINT_CANCELLED,
                     Events.PRINT_FAILED, Events.PRINT_DONE):
            self._triggered = set()
            # Notify JS to reset triggered indicators in sidebar
            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(type="print_reset"),
            )

    # ── GCODE hook ────────────────────────────────────────────────────────────

    def gcode_queuing_hook(
        self, comm_instance, phase, cmd, cmd_type, gcode,
        subcode=None, tags=None, *args, **kwargs
    ):
        if not cmd:
            return

        layer = None

        # Cura / Ultimaker: ;LAYER:0  (0-indexed → 1-indexed)
        if cmd.upper().startswith(";LAYER:"):
            try:
                layer = int(cmd.split(":")[1].strip()) + 1
            except (ValueError, IndexError):
                pass

        # PrusaSlicer / SuperSlicer: ; layer 1, Z = 0.2
        elif cmd.lower().startswith("; layer "):
            try:
                layer = int(cmd.split()[2].strip(","))
            except (ValueError, IndexError):
                pass

        if layer is not None:
            self._process_layer(layer)

    def _process_layer(self, layer_num):
        if layer_num in self._triggered:
            return

        layers = self._settings.get(["layers"]) or []
        for entry in layers:
            if not entry.get("enabled", True):
                continue
            if entry.get("layer") != layer_num:
                continue

            self._triggered.add(layer_num)
            command = (entry.get("command") or "").strip()

            self._logger.info(
                "Layer %d reached. GCODE command: %s", layer_num, command or "—"
            )

            # Send GCODE command to printer if configured
            if command and self._printer and self._printer.is_printing():
                self._printer.commands([command])

            # Push notification to browser (includes sound settings so JS can play)
            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(
                    type="layer_reached",
                    layer=layer_num,
                    command=command,
                    sound_enabled=self._settings.get_boolean(["sound_enabled"]),
                    sound_type=self._settings.get(["sound_type"]),
                    sound_volume=self._settings.get_float(["sound_volume"]),
                ),
            )
            break  # one entry per layer is enough

    # ── REST API ──────────────────────────────────────────────────────────────

    def on_api_get(self, request):
        return flask.jsonify(
            layers=self._settings.get(["layers"]) or []
        )

    def get_api_commands(self):
        return dict(test_notify=["layer", "command"])

    def on_api_command(self, command, data):
        if command == "test_notify":
            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(
                    type="layer_reached",
                    layer=int(data.get("layer", 1)),
                    command=data.get("command", ""),
                    sound_enabled=self._settings.get_boolean(["sound_enabled"]),
                    sound_type=self._settings.get(["sound_type"]),
                    sound_volume=self._settings.get_float(["sound_volume"]),
                ),
            )
        return flask.jsonify({})


# ── Plugin registration ────────────────────────────────────────────────────────

__plugin_name__ = "Layer Notify"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = LayerNotifyPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
    }
