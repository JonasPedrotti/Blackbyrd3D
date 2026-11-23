# Contributing to Blackbyrd3D

Thanks for looking under the hood. Bug reports, commands, and file-format
work are all welcome — this project aims to be a serious NURBS modeller
for Linux, and it gets there faster with more hands.

## Dev setup

```bash
git clone https://github.com/JonasPedrotti/Blackbyrd3D.git
cd Blackbyrd3D
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/byrd3d                # run the app
```

Python ≥ 3.10. The heavy dependency is `cadquery-ocp` (OpenCASCADE 7.9
prebuilt as pybind11 bindings) — it's a large wheel, but there is nothing
to compile.

## Running the tests

The `dev` extra brings `pytest` and `pytest-xdist`. From the repository root:

```bash
# Linux / macOS
.venv/bin/pytest -n 8                                  # the whole suite, eight at a time
.venv/bin/pytest tests/test_rhino_text_comes_in_as_editable_text.py   # one file
.venv/bin/pytest tests -k fillet                       # every test with "fillet" in its name
```

```powershell
# Windows
.venv\Scripts\python -m pytest -n 8
```

The suite has about 6,800 tests and takes around two minutes with eight
workers. Each test brings its own settings, journal and autosave
directories, so `-n` can run them side by side.

Things worth knowing:

- **No windows pop up.** `tests/conftest.py` runs Qt headless
  (`QT_QPA_PLATFORM=offscreen`) unless you set the variable yourself. Set it
  to `xcb` (Linux) or `windows` to watch the viewports on screen.
- **Choose `-n` by memory, not cores.** A worker peaks at about 2.5 GB, so
  eight need around 13 GB of RAM. With less, use `-n 4`. Avoid `-n auto` on
  a machine with many cores.
- **Progress** shows as `[ 45%]` at the end of each line. Leave out `-q`
  to see it.
- **A run that stops moving** (say at 97%) almost always means a test is
  waiting on a helper process that died, for example in the parallel 3DM
  import. Run that test file on its own without `-n`; a native crash then
  shows up as an exit code instead of a hang.
- Leave `-n` off when you suspect a test leaves something behind for the
  next one. That is the one thing running them apart can hide.

If you change behaviour, add or update a test that would have caught the
regression.

### GitHub Actions

The workflows live in `.github/workflows/`.

| Workflow            | Runs                                   | What it does                                                        |
| ------------------- | -------------------------------------- | ------------------------------------------------------------------- |
| `ci.yml`            | on every push to `main` and every PR   | Installs with `uv sync --extra dev --locked`, runs `pytest -n auto` headless on Ubuntu, then a `byrd3d-batch` smoke test (box, fillet, STEP and glTF export). |
| `tests-windows.yml` | by hand                                | The same suite on Windows, catching what only breaks there (encodings, paths, fonts). |
| `build-*.yml`       | when a release is published, or by hand | Builds the Windows installer, macOS disk image or Linux AppImage after a short startup test and attaches it to the release. |

CI skips commits that only touch Markdown, `docs/` or `assets/`, and a
newer push to the same branch cancels the run still going. PRs need it
green.

To start a workflow by hand, open it on GitHub under **Actions** and choose
**Run workflow**, or use the command line:

```bash
gh workflow run tests-windows.yml   # the suite on Windows
gh run watch                        # follow the run in the terminal
```

CI installs from `uv.lock`, so a dependency added to `pyproject.toml`
needs `uv lock` before it reaches CI. The runners have four cores and
16 GB, which is why `-n auto` is safe there and not necessarily on your
machine.

## Where things live

```
blackbyrd3d/
├── core/          # kernel layer: geometry builders, tessellation,
│                  #   scene graph, layers, selection, undo history
├── commands/      # generator-based interactive commands
├── ui/            # Qt: GL viewport, command line, panels
├── fileio/        # .byrd / STEP / OBJ / glTF / DXF / SVG / USD
└── mcp_server/    # stdio MCP server -> RPC bridge
```

Two rules keep the layers clean:

1. **All OCP/OpenCASCADE imports stay in `core/`** (mostly
   `core/geometry.py`). Commands and UI talk to shapes only through the
   `core` API — this is what keeps commands testable without a display
   and the kernel swappable in principle.
2. **Commands never touch Qt.** A command is a Python generator that
   yields typed requests (`PointReq`, `NumberReq`, `SelectReq`, …) and
   receives the answer back — the same code serves viewport clicks,
   typed input, macros, and MCP calls.

## Adding a command

The generator protocol in one example:

```python
from .base import PointReq, NumberReq, command
from ..core import geometry as g

@command("tube", aliases=("tu",))
def cmd_tube(ctx):
    centre = yield PointReq("Centre of tube")
    radius = yield NumberReq("Radius", default=5.0)
    ctx.scene.add(g.make_cylinder(centre, radius, radius * 4), name="Tube")
    ctx.echo("Tube created.")
```

Registering it (import the module in `commands/__init__.py`) gets you
prompts, osnaps, undo, aliasing, macro support, and MCP exposure for
free. Look at `commands/curves.py` and `commands/transform.py` for
fuller examples — previews (`preview_fn`), option chips (`choices`),
and reference-point input are all shown there.

If the command exists in Rhino, keep its name and prompt order —
matching existing muscle memory is a design goal, not an accident.

## Pull requests

- Keep PRs focused; separate refactors from behaviour changes.
- Match the surrounding style (the codebase is plain PEP 8, no
  formatter is enforced).
- Describe *what a user can now do*, not just what the code does.
- Screenshots or a short capture for anything visual — there's a
  built-in `viewcapturetofile` command that helps.

Not sure whether an idea fits? Open an issue or a discussion first —
cheap to talk, expensive to rewrite.
