# Roadmap

Where Blackbyrd3D is heading, in rough order. There are no dates, and
priorities can shift as the project grows.

If you run into problems, please open an
[Issue](https://github.com/JonasPedrotti/Blackbyrd3D/issues/new/choose).
I read every issue, and I try
to prioritise them: crashes and lost work first, then bugs that block real
work, then everything else.

## 1. Solid basics

Fixing, testing and more fixing. Before anything new gets built on top, what
is already there has to be reliable.

- Fix the bugs that are reported and the ones that are still hiding.
- Grow the test suite so fixed bugs stay fixed.
- Smooth out rough edges in the interface, file handling and performance.
- Keep Windows, macOS and Linux builds working the same way.
- Sign the Windows installer, through SignPath Foundation's free programme
  for open source, so Windows stops warning about an unknown publisher.
- Linux: let a torn-off Wyrm window be dragged by its title bar again after
  it was docked once, and centre dialogs on COSMIC, which places windows
  itself.
- Curved surfaces stay smooth when zoomed in close: the faces in view are
  meshed finer, so a shaded outline no longer stands out past its edge.
- Draw on a face: the first point of a drawing command takes the plane of
  the flat face under the cursor.
- `splitface` and `insetface`: split a face or inset it without the object
  falling apart.
- SpaceMouse support on Windows and macOS, as on Linux already.
- A full command list on the documentation site.

## 2. Expanding the base

More commands for modelling and drafting, so everyday work does not run
into missing tools.

- Fill in the core modelling commands that are still missing.
- More drafting tools: dimensions, annotations and layout.
- Better import and export for common file formats.
- Export a ready to render scene for Blender and Cycles, with cameras,
  lights and materials.
- An anaglyph stereo view for red and cyan glasses, with adjustable eye
  separation and focal length.
- Translations of the interface into other languages.
- A project website, on GitHub Pages or its own domain, once enough people
  show interest in Blackbyrd3D. GitHub stars are a good signal for that.

## 3. Wyrm

Grow the node editor into a real way to build and drive models.

- More components for geometry, math, lists and data.
- More ways to drive the model from a graph and feed results back into it.
- Better handling of large graphs and clearer feedback when something fails.

## 4. Laser

Laser cutting and engraving, primarily for **Ruida controllers**.

- The basics: clean 2D output, with what is cut and what is engraved kept
  apart, plus speed, power and passes per layer.
- A preview that shows the job and its order before it runs.
- Direct communication with your laser: send jobs, frame the work area and
  control the machine right from Blackbyrd3D.

## 5. CAM

Basic CNC toolpaths, primarily for **GRBL** controllers, including the
popular Arduino Nano based boards.

- Simple 2D and 2.5D toolpaths: profiles, pockets and drilling.
- Tool and material settings with sensible defaults.
- G-code output that GRBL understands, and a preview of the toolpath.

Ideas and requests are welcome on
[GitHub](https://github.com/JonasPedrotti/Blackbyrd3D).
