# OctoPrint Layer Notify

[![OctoPrint](https://img.shields.io/badge/OctoPrint-1.4.0+-blue.svg)](https://octoprint.org)
[![Python](https://img.shields.io/badge/Python-3.x-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-AGPLv3-orange.svg)](LICENSE)

> Receive visual and sound alerts in OctoPrint when specific layers are reached during printing — with optional GCODE commands per layer.

---

## Features

- **Multiple target layers** — configure as many layers as you need, each independently
- **GCODE command per layer** — execute any GCODE when a layer is reached (e.g. `M600` for filament change)
- **Browser notification** — toast inside OctoPrint + native OS notification (Windows / macOS / Android)
- **Configurable sound alert** — 4 built-in sounds, adjustable volume and repeat count
- **Dedicated tab** — real-time status showing which layers have fired and which are waiting
- **Universal slicer support** — works with Cura, PrusaSlicer, SuperSlicer and any slicer via Z-movement detection
- **Per-print reset** — each layer fires only once per print job

---

## Screenshots

| Settings panel | Layer Notify tab |
|:-:|:-:|
| ![Settings](https://raw.githubusercontent.com/Benaa42/octoprint-layer-notify/main/docs/screenshot_settings.png) | ![Tab](https://raw.githubusercontent.com/Benaa42/octoprint-layer-notify/main/docs/screenshot_tab.png) |

---

## Installation

### Via OctoPrint Plugin Manager (recommended)

1. Open OctoPrint → **Settings → Plugin Manager → Get More**
2. Paste the URL below in the **"… from URL"** field:
   ```
   https://github.com/Benaa42/octoprint-layer-notify/archive/main.zip
   ```
3. Click **Install** and restart OctoPrint when prompted.

### Manual

```bash
~/oprint/bin/pip install https://github.com/Benaa42/octoprint-layer-notify/archive/main.zip
sudo service octoprint restart
```

---

## Configuration

Go to **Settings → Layer Notify**.

### Adding a layer

| Field | Description |
|-------|-------------|
| **Layer** | Layer number to watch (1-indexed) |
| **GCODE Command** | Optional command sent to printer when layer is reached (e.g. `M600`, `M117 Check print`, `M300 S880 P500`) |
| **Active** | Enable/disable this entry without deleting it |

Click **+ Add layer**, fill in the fields, then **Save**.

### Sound alert

| Setting | Description |
|---------|-------------|
| **Enabled** | Toggle all sounds on/off |
| **Sound type** | Single beep · Three beeps · Alternating alarm · Rising tone |
| **Repetitions** | How many times the sound plays (1–10) |
| **Volume** | 0 – 100% |

Click **Listen** to preview the current sound configuration.

### Common GCODE commands

| Command | Effect |
|---------|--------|
| `M600` | Filament change (pauses print, waits for user) |
| `M25` | Pause print |
| `M117 Your message` | Show message on printer display |
| `M300 S880 P500` | Beep on the printer |

---

## Slicer compatibility

| Slicer | Layer comment format | Supported |
|--------|---------------------|-----------|
| Cura / Ultimaker Cura | `;LAYER:0` (0-indexed) | ✅ |
| PrusaSlicer / SuperSlicer | `; layer 1, Z = 0.2` | ✅ |
| Any slicer | Z-movement detection | ✅ |

Layer detection works automatically — no slicer configuration needed.

---

## Requirements

- OctoPrint ≥ 1.4.0
- Python 3

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss what you would like to change.

---

## License

[GNU AGPLv3](LICENSE)
