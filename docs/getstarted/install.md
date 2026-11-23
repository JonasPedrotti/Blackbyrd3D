# Install

## Download

Each build bundles the OpenCASCADE kernel and Python runtime — nothing else
to install.

| Platform | Download |
|---|---|
| **Linux** | [`Blackbyrd3D-x86_64.AppImage`](https://github.com/JonasPedrotti/Blackbyrd3D/releases/latest/download/Blackbyrd3D-x86_64.AppImage) — `chmod +x` and run |
| **Windows** | [`Blackbyrd3D-Setup-x86_64.exe`](https://github.com/JonasPedrotti/Blackbyrd3D/releases/latest/download/Blackbyrd3D-Setup-x86_64.exe) — installer ([Privacy](../privacy.md)) |
| **macOS** (Apple Silicon, macOS 14 or newer) | [`Blackbyrd3D-arm64.dmg`](https://github.com/JonasPedrotti/Blackbyrd3D/releases/latest/download/Blackbyrd3D-0.1.0-arm64.dmg) - drag to Applications, then on first launch **System Settings > Privacy & Security > Open Anyway** |

The GUI needs a GPU with OpenGL 3.3 drivers (any normal desktop). Headless
use (`byrd3d-batch`, the MCP server, file conversion) works anywhere.

## From source

Requires Python 3.10+. Works on Linux, Windows and macOS.

```bash
git clone https://github.com/JonasPedrotti/Blackbyrd3D
cd Blackbyrd3D
python3 -m venv .venv
.venv/bin/pip install -e .        # or: uv pip install -e .
.venv/bin/byrd3d
```

The heavy dependency is `cadquery-ocp` (the OpenCASCADE kernel); everything
installs from PyPI wheels — no conda, no compiler. The full test suite passes
on all three platforms.

## Entry points

| Command | What it starts |
|---|---|
| `byrd3d` | the GUI |
| `byrd3d file.byrd` | the GUI with a file |
| `byrd3d-batch script.py` | headless scripting (no display needed) |
| `byrd3d-mcp` | the MCP server for AI clients |

## AppImage

A self-contained AppImage recipe lives in `packaging/appimage`:

```bash
./packaging/appimage/build-appimage.sh
```

## SpaceMouse

3Dconnexion devices work out of the box when
[spacenavd](https://spacenav.sourceforge.net/) is running
(`sudo apt install spacenavd`) — Blackbyrd3D speaks the daemon's
socket directly, on X11 and Wayland alike. Slide to pan, push/pull to
zoom, tilt/twist to orbit; buttons default to Fit and Perspective.
Sensitivity and inversion live in *Settings → Mouse*; the `spacemouse`
command shows status and a live axis readout (`Diag`).

## Configuration

Settings live in `~/.config/blackbyrd3d/config.json` (edit through
*Tools → Settings*). A `template.byrd` in the same directory becomes
the startup template. Autosaves land in `~/.blackbyrd3d/autosave` and
are offered for recovery after a crash.
