# Contributing to Blackbyrd3D

Thanks for looking under the hood. Bug reports, commands and file-format
work are all welcome. This project aims to be a serious NURBS modeller for
Linux, Windows and macOS, and it gets there faster with more hands.

## Dev setup

You need Python 3.10 or later and Git. The heavy dependency is
`cadquery-ocp` (OpenCASCADE 7.9 as prebuilt Python bindings). It is a large
download, but there is nothing to compile.

Linux and macOS:

```bash
git clone https://github.com/JonasPedrotti/Blackbyrd3D.git
cd Blackbyrd3D
python3 -m venv .venv                # a Python environment just for Blackbyrd3D
.venv/bin/pip install -e ".[dev]"    # the app in editable mode, plus the test tools
.venv/bin/byrd3d                     # start the app
```

Windows (PowerShell):

```powershell
git clone https://github.com/JonasPedrotti/Blackbyrd3D.git
cd Blackbyrd3D
py -m venv .venv                       # a Python environment just for Blackbyrd3D
.venv\Scripts\pip install -e ".[dev]"  # the app in editable mode, plus the test tools
.venv\Scripts\byrd3d                   # start the app
```

"Editable" means your changes to the source take effect the next time you
start the app, without installing again.

## Running the tests

The `dev` extra brings `pytest` and `pytest-xdist`. Run these from the
repository root.

Linux and macOS:

```bash
.venv/bin/pytest -n 8                                                  # the whole suite, eight tests at a time
.venv/bin/pytest tests/test_rhino_text_comes_in_as_editable_text.py   # one test file
.venv/bin/pytest tests -k fillet                                       # every test with "fillet" in its name
```

Windows (PowerShell):

```powershell
.venv\Scripts\pytest -n 8                                                  # the whole suite, eight tests at a time
.venv\Scripts\pytest tests\test_rhino_text_comes_in_as_editable_text.py   # one test file
.venv\Scripts\pytest tests -k fillet                                       # every test with "fillet" in its name
```

The suite has about 7,000 tests and takes a few minutes with eight
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

| Workflow            | Runs                                    | What it does |
| ------------------- | --------------------------------------- | ------------ |
| `ci.yml`            | on every push to `main` and every PR    | Installs with `uv sync --extra dev --locked`, runs `pytest -n auto` headless on Ubuntu, then a `byrd3d-batch` smoke test (box, fillet, STEP and glTF export). |
| `tests-windows.yml` | by hand                                 | The same suite on Windows, catching what only breaks there (encodings, paths, fonts). |
| `build-*.yml`       | when a release is published, or by hand | Builds the Windows installer, macOS disk image or Linux AppImage after a short startup test and attaches it to the release. |

CI skips commits that only touch Markdown, `docs/` or `assets/`, and a
newer push to the same branch cancels the run still going. PRs need it
green.

To start a workflow by hand, open it on GitHub under **Actions** and choose
**Run workflow**, or use the [GitHub CLI](https://cli.github.com):

```bash
gh workflow run tests-windows.yml   # start the suite on Windows
gh run watch                        # follow the run in the terminal
```

CI installs from `uv.lock`, so a dependency added to `pyproject.toml`
needs `uv lock` before it reaches CI. The runners have four cores and
16 GB, which is why `-n auto` is safe there and not necessarily on your
machine.

## Where things live

```
blackbyrd3d/
├── core/          # the geometry layer: shapes, meshing for display,
│   │              #   scene, layers, selection, undo history
│   └── wyrm/      # the node graph engine behind Wyrm
├── commands/      # every command you can type, one module per topic
├── ui/            # Qt: the viewports, command line, panels and dialogs
│   └── wyrm/      # Wyrm's node editor
├── fileio/        # reading and writing files: .byrd, 3DM, STEP, DXF, SVG, ...
├── ai/            # the assistant and its providers
└── mcp_server/    # lets an MCP client (an AI app) drive a running session
```

Two rules keep the layers clean:

1. **All OCP/OpenCASCADE imports stay in `core/`** (mostly
   `core/geometry.py`). Commands and UI talk to shapes only through the
   `core` API. That keeps commands testable without a display, and the
   kernel replaceable in principle.
2. **Commands never touch Qt.** A command is a Python generator: it
   `yield`s a request such as `PointReq`, `NumberReq` or `SelectReq`, and
   gets the answer back as the value of that `yield`. The same code then
   serves clicks in the viewport, typed input, macros and MCP calls.

## Adding a command

A complete command, in a new or existing module under
`blackbyrd3d/commands/`:

```python
from .base import NumberReq, PointReq, command
from ..core import geometry as g


@command("tube", aliases=("tu",))      # typed as "tube" or "tu"
def cmd_tube(ctx):
    # Each yield asks the user, and pauses here until they answer.
    centre = yield PointReq("Centre of tube")
    radius = yield NumberReq("Radius", default=5.0)

    # make_cylinder(base point, radius, height) builds the solid,
    # scene.add puts it in the model.
    ctx.scene.add(g.make_cylinder(centre, radius, radius * 4), name="Tube")
    ctx.echo("Tube created.")             # a line in the command history
```

A new module also needs an import in `commands/__init__.py`. That is all:
prompts, object snaps, undo, aliases, macros and MCP access come with it.
`commands/curves.py` and `commands/transform.py` show more, such as a live
preview while picking (`preview_fn`), clickable options (`choices`) and
reference points.

If the command exists in Rhino, keep its name and prompt order. Matching
existing muscle memory is a design goal, not an accident.

## Pull requests

- Keep PRs focused; separate refactors from behaviour changes.
- Match the surrounding style (plain PEP 8; no formatter is enforced).
- Describe *what a user can now do*, not just what the code does.
- Add screenshots or a short capture for anything visual. The built-in
  `viewcapturetofile` command helps.

Not sure whether an idea fits? Open an issue or a discussion first. It is
cheap to talk and expensive to rewrite.
