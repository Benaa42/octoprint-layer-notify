$(function () {

    // ── Audio engine ───────────────────────────────────────────────────────────

    var _audioCtx = null;

    function _getCtx() {
        if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (_audioCtx.state === "suspended") _audioCtx.resume();
        return _audioCtx;
    }

    function _tone(freq, start, dur, vol, type) {
        var ctx = _getCtx(), osc = ctx.createOscillator(), g = ctx.createGain();
        osc.connect(g); g.connect(ctx.destination);
        osc.type = type || "sine";
        osc.frequency.setValueAtTime(freq, start);
        g.gain.setValueAtTime(vol, start);
        g.gain.exponentialRampToValueAtTime(0.001, start + dur);
        osc.start(start); osc.stop(start + dur);
    }

    var _sounds = {
        single: function (v) { var c = _getCtx(); _tone(880, c.currentTime, 0.5, v); },
        triple: function (v) { var c = _getCtx(), t = c.currentTime; _tone(880, t, 0.18, v); _tone(880, t + 0.25, 0.18, v); _tone(880, t + 0.5, 0.18, v); },
        alarm:  function (v) { var c = _getCtx(), t = c.currentTime; for (var i = 0; i < 4; i++) { _tone(440, t + i * 0.3, 0.14, v, "square"); _tone(880, t + i * 0.3 + 0.15, 0.14, v, "square"); } },
        rising: function (v) { var c = _getCtx(), o = c.createOscillator(), g = c.createGain(); o.connect(g); g.connect(c.destination); o.type = "sine"; o.frequency.setValueAtTime(300, c.currentTime); o.frequency.exponentialRampToValueAtTime(1200, c.currentTime + 0.8); g.gain.setValueAtTime(v, c.currentTime); g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.8); o.start(c.currentTime); o.stop(c.currentTime + 0.8); }
    };

    // Duration in ms of each sound type (gap between repetitions)
    var _soundDuration = { single: 700, triple: 1000, alarm: 1600, rising: 1100 };

    function _playSound(type, volume, repeat) {
        var fn    = _sounds[type] || _sounds.triple;
        var vol   = volume || 0.5;
        var times = Math.max(1, Math.min(parseInt(repeat, 10) || 1, 10));
        var gap   = _soundDuration[type] || 1000;

        for (var i = 0; i < times; i++) {
            (function (index) {
                setTimeout(function () {
                    try { fn(vol); } catch (e) {}
                }, index * gap);
            })(i);
        }
    }

    // Helper: safe access to plugin settings observable
    function _ps(self) {
        try { return self.settingsViewModel.settings.plugins.layer_notify; } catch (e) { return null; }
    }

    // ── ViewModel ──────────────────────────────────────────────────────────────

    function LayerNotifyViewModel(parameters) {
        var self = this;
        self.settingsViewModel = parameters[0];

        self.layerList       = ko.observableArray([]);
        self.triggeredLayers = ko.observableArray([]);

        self.isTriggered = function (layerNum) {
            return self.triggeredLayers().indexOf(parseInt(layerNum, 10)) >= 0;
        };

        // ── Startup: fetch layers from server so the tab has data immediately ──

        self.onStartupComplete = function () {
            OctoPrint.simpleApiGet("layer_notify")
                .done(function (data) {
                    _applyLayers(data.layers || []);
                })
                .fail(function () {
                    console.warn("LayerNotify: failed to fetch layers from API");
                });
        };

        // ── Settings dialog: serialize before save ─────────────────────────────

        self.onSettingsBeforeSave = function () {
            var ps = _ps(self);
            if (!ps) return;
            var data = self.layerList().map(function (item) {
                return {
                    layer:   parseInt(ko.unwrap(item.layer), 10),
                    command: ko.unwrap(item.command),
                    enabled: ko.unwrap(item.enabled)
                };
            });
            ps.layers(data);
        };

        // ── Table actions ─────────────────────────────────────────────────────

        self.addLayer = function () {
            self.layerList.push({
                layer:   ko.observable(1),
                command: ko.observable(""),
                enabled: ko.observable(true)
            });
        };

        self.removeLayer = function (item) {
            self.layerList.remove(item);
        };

        self.testEntry = function (item) {
            OctoPrint.simpleApiCommand("layer_notify", "test_notify", {
                layer:         parseInt(ko.unwrap(item.layer), 10),
                command_gcode: ko.unwrap(item.command)
            });
        };

        self.previewSound = function () {
            var ps = _ps(self);
            if (!ps) { _playSound("triple", 0.5, 1); return; }
            _playSound(
                ko.unwrap(ps.sound_type),
                parseFloat(ko.unwrap(ps.sound_volume)) || 0.5,
                parseInt(ko.unwrap(ps.sound_repeat), 10) || 1
            );
        };

        // ── Plugin messages ────────────────────────────────────────────────────

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "layer_notify") return;

            if (data.type === "print_reset") {
                self.triggeredLayers([]);
                return;
            }
            if (data.type !== "layer_reached") return;

            self.triggeredLayers.push(parseInt(data.layer, 10));

            if (data.sound_enabled) _playSound(data.sound_type, data.sound_volume, data.sound_repeat);

            var cmdPart = data.command
                ? "<br><small>Command sent: <code>" + _escHtml(data.command) + "</code></small>"
                : "";
            new PNotify({
                title:       "Layer Notify",
                text:        "Layer <strong>" + _escHtml(String(data.layer)) + "</strong> reached!" + cmdPart,
                type:        "info",
                hide:        false,
                buttons:     { closer: true, sticker: false },
                icon:        "fa fa-print",
                text_escape: false
            });

            _nativeNotify(
                "Layer " + data.layer + " reached!",
                data.command ? "Command sent: " + data.command : "Check your print."
            );
        };
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    function _escHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function _applyLayers(raw) {
        LayerNotifyViewModel._instance.layerList(raw.map(function (item) {
            return {
                layer:   ko.observable(item.layer   || 1),
                command: ko.observable(item.command || ""),
                enabled: ko.observable(item.enabled !== false)
            };
        }));
    }

    function _nativeNotify(title, body) {
        if (!("Notification" in window)) return;
        var payload = { body: title + "\n" + body, icon: "/static/img/tentacle-20x20.png" };
        if (Notification.permission === "granted") {
            new Notification("OctoPrint – Layer Notify", payload);
        } else if (Notification.permission === "default") {
            Notification.requestPermission().then(function (p) {
                if (p === "granted") new Notification("OctoPrint – Layer Notify", payload);
            });
        }
    }

    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: function (parameters) {
            var vm = new LayerNotifyViewModel(parameters);
            LayerNotifyViewModel._instance = vm;
            return vm;
        },
        dependencies: ["settingsViewModel"],
        elements:     [
            "#settings_plugin_layer_notify",
            "#tab_plugin_layer_notify"
        ]
    });

});
