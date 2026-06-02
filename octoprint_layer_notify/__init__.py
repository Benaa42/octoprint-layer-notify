import flask
import octoprint.plugin
from octoprint.events import Events


class LayerNotifyPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.BlueprintPlugin,
):
    def __init__(self):
        self._triggered    = set()   # layer numbers fired this print
        self._current_z    = 0.0     # most recent Z coordinate seen
        self._last_layer_z = 0.0     # Z of last confirmed layer change
        self._z_layer_count = 0      # sequential layer counter (Z-based)

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings_defaults(self):
        return dict(
            layers=[],
            sound_enabled=True,
            sound_type="triple",
            sound_volume=0.5,
            sound_repeat=2,
        )

    # ── Templates ─────────────────────────────────────────────────────────────

    def get_template_configs(self):
        return [
            dict(type="settings", template="layer_notify_settings.jinja2", custom_bindings=True),
            dict(type="tab",      template="layer_notify_tab.jinja2",      custom_bindings=True, name="Layer Notify"),
        ]

    # ── Assets ────────────────────────────────────────────────────────────────

    def get_assets(self):
        return dict(js=["js/layer_notify.js"])

    # ── Events ────────────────────────────────────────────────────────────────

    def on_event(self, event, payload):
        if event in (Events.PRINT_STARTED, Events.PRINT_CANCELLED,
                     Events.PRINT_FAILED, Events.PRINT_DONE):
            self._triggered     = set()
            self._current_z     = 0.0
            self._last_layer_z  = 0.0
            self._z_layer_count = 0
            self._plugin_manager.send_plugin_message(
                self._identifier, dict(type="print_reset")
            )

    # ── GCODE hook ────────────────────────────────────────────────────────────

    def gcode_queuing_hook(
        self, comm_instance, phase, cmd, cmd_type, gcode,
        subcode=None, tags=None, *args, **kwargs
    ):
        if not cmd:
            return

        layer = None

        # ── Method 1: slicer layer comments ───────────────────────────────────
        # Cura / Ultimaker Cura: ;LAYER:0  (0-indexed → convert to 1-indexed)
        if cmd.upper().startswith(";LAYER:"):
            try:
                layer = int(cmd.split(":")[1].strip()) + 1
                self._logger.debug("LayerNotify comment layer: %d", layer)
            except (ValueError, IndexError):
                pass

        # PrusaSlicer / SuperSlicer: ; layer 1, Z = 0.2  (1-indexed)
        elif cmd.lower().startswith("; layer "):
            try:
                layer = int(cmd.split()[2].strip(",."))
                self._logger.debug("LayerNotify PrusaSlicer layer: %d", layer)
            except (ValueError, IndexError):
                pass

        # ── Method 2: Z-movement detection (any slicer) ───────────────────────
        # Tracks Z coordinate and counts a new layer when extrusion happens
        # at a Z level higher than the previous layer — avoids Z-hop false positives.
        if layer is None and gcode in ("G0", "G1", "G00", "G01"):
            z_val  = None
            has_e  = False
            for part in cmd.upper().split():
                if part.startswith("Z"):
                    try:
                        z_val = float(part[1:])
                    except ValueError:
                        pass
                elif part.startswith("E"):
                    has_e = True

            if z_val is not None:
                self._current_z = z_val

            # New layer = first extrusion at a Z higher than the last layer Z
            if has_e and self._current_z > self._last_layer_z + 0.01:
                self._last_layer_z = self._current_z
                self._z_layer_count += 1
                layer = self._z_layer_count
                self._logger.debug(
                    "LayerNotify Z-based layer: %d (Z=%.3f)", layer, self._current_z
                )

        if layer is not None:
            self._process_layer(layer)

    # ── Layer processing ──────────────────────────────────────────────────────

    def _process_layer(self, layer_num):
        layer_num = int(layer_num)

        if layer_num in self._triggered:
            return

        layers = self._settings.get(["layers"]) or []

        for entry in layers:
            if not entry.get("enabled", True):
                continue
            # Coerce both sides to int to avoid string vs int mismatch
            if int(entry.get("layer", -1)) != layer_num:
                continue

            self._triggered.add(layer_num)
            command = (entry.get("command") or "").strip()

            self._logger.info(
                "LayerNotify: layer %d reached — command: %s", layer_num, command or "none"
            )

            if command and self._printer and self._printer.is_printing():
                self._printer.commands([command])

            self._plugin_manager.send_plugin_message(
                self._identifier,
                dict(
                    type="layer_reached",
                    layer=layer_num,
                    command=command,
                    sound_enabled=self._settings.get_boolean(["sound_enabled"]),
                    sound_type=self._settings.get(["sound_type"]),
                    sound_volume=self._settings.get_float(["sound_volume"]),
                    sound_repeat=self._settings.get_int(["sound_repeat"]),
                ),
            )
            break

    # ── REST API ──────────────────────────────────────────────────────────────

    def is_api_protected(self):
        return True

    def on_api_get(self, request):
        return flask.jsonify(layers=self._settings.get(["layers"]) or [])

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
                    sound_repeat=self._settings.get_int(["sound_repeat"]),
                ),
            )
        return flask.jsonify({})

    # ── Software update hook ───────────────────────────────────────────────────

    def get_update_information(self):
        return dict(
            layer_notify=dict(
                displayName="Layer Notify",
                displayVersion=self._plugin_version,
                type="github_release",
                user="Benaa42",
                repo="octoprint-layer-notify",
                current=self._plugin_version,
                pip="https://github.com/Benaa42/octoprint-layer-notify/archive/{target_version}.zip",
            )
        )

    # ── Jinja2 template autoescaping ──────────────────────────────────────────

    def is_template_autoescaped(self):
        return True


# ── Plugin registration ────────────────────────────────────────────────────────

__plugin_name__ = "Layer Notify"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = LayerNotifyPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
    }
