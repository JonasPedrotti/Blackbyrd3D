"""Builds the example models in blackbyrd3d/examples and their README
screenshots in assets/examples.

Needs a display, since the thumbnails and screenshots are taken from the
real window. From the repository root:

    .venv/Scripts/python packaging/examples/make_examples.py

--only NAME builds one example, --shots-only retakes the screenshots of
the .byrd files as they are, without building or saving them, and
--reframe keeps a .byrd as it was drawn but sets its view again, saves it
and retakes its screenshots.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp(prefix="byrd_examples_")
os.environ["BYRD3D_CONFIG"] = os.path.join(_TMP, "settings.json")
os.environ["BYRD3D_JOURNAL_DIR"] = os.path.join(_TMP, "journals")
os.environ["BYRD3D_AUTOSAVE_DIR"] = os.path.join(_TMP, "autosave")
os.environ["BYRD3D_NO_WELCOME"] = "1"
os.environ["BYRD3D_NO_RPC"] = "1"

from PySide6.QtCore import QBuffer, QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

EXAMPLES_DIR = os.path.join(ROOT, "blackbyrd3d", "examples")
SHOTS_DIR = os.path.join(ROOT, "assets", "examples")


def _layer(scene, name, color):
    found = scene.layers.find_by_name(name)
    return (found or scene.layers.create(name, color=color)).id


def build_detail(scene, geo):
    """A construction detail in millimetres, drawn flat: a floor-to-ceiling
    window where the floor slab meets the terrace, inside to the left,
    outside to the right. y is the height, 0 the finished floor."""
    from blackbyrd3d.core.hatch import HatchShape
    scene.units = "mm"
    concrete_l = _layer(scene, "Concrete", (0.80, 0.80, 0.82))
    screed_l = _layer(scene, "Screed", (0.74, 0.72, 0.66))
    insul_l = _layer(scene, "Insulation", (0.95, 0.78, 0.30))
    finish_l = _layer(scene, "Parquet", (0.80, 0.60, 0.40))
    frame_l = _layer(scene, "Window frame", (0.85, 0.86, 0.88))
    glass_l = _layer(scene, "Glazing", (0.55, 0.78, 0.95))
    seal_l = _layer(scene, "Seals", (0.30, 0.30, 0.32))
    membrane_l = _layer(scene, "Membrane", (0.35, 0.55, 0.95))
    metal_l = _layer(scene, "Drainage", (0.70, 0.72, 0.76))
    stone_l = _layer(scene, "Paving", (0.78, 0.76, 0.72))
    gravel_l = _layer(scene, "Gravel", (0.66, 0.62, 0.56))
    earth_l = _layer(scene, "Earth", (0.62, 0.52, 0.40))

    def pts3(pts):
        return [(x, y, 0) for x, y in pts]

    def poly(pts, layer, name, closed=True):
        scene.add(geo.make_polyline(pts3(pts), closed=closed), name=name,
                  layer_id=layer)

    def rect(x0, y0, x1, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    def cut(pts, layer, name, pattern, angle, spacing, outline=True):
        if outline:
            poly(pts, layer, name)
        region = geo.planar_face(geo.make_polyline(pts3(pts), closed=True))
        scene.add(HatchShape(region, pattern, angle=angle, spacing=spacing,
                             xdir=(1, 0, 0)),
                  name=f"{name} hatch", layer_id=layer)

    # inside: the floor build-up on the slab, which runs under the window
    cut(rect(-1200, -365, 200, -115), concrete_l, "Reinforced concrete slab",
        "cross", 45, 30)
    cut(rect(-1200, -115, 60, -75), insul_l, "Impact sound insulation",
        "lines", 90, 8)
    cut(rect(-1200, -75, 60, -15), screed_l, "Screed", "dots", 0, 14)
    cut(rect(-1200, -15, 60, 0), finish_l, "Parquet", "lines", 0, 5)
    poly(rect(60, -115, 70, 0), seal_l, "Edge strip")

    # the window: an insulated base, the outer frame, the sash and the
    # triple glazing held in it
    cut(rect(70, -115, 200, -40), insul_l, "Insulated base", "lines", -45,
        12)
    poly(rect(80, -40, 200, 20), frame_l, "Outer frame")
    poly(rect(92, -28, 188, 8), frame_l, "Frame chamber")
    poly(rect(90, 20, 190, 110), frame_l, "Sash")
    poly(rect(100, 30, 180, 60), frame_l, "Sash chamber")
    for x0 in (110, 134, 158):
        poly(rect(x0, 95, x0 + 6, 700), glass_l, "Glass pane")
    for x0 in (116, 140):
        cut(rect(x0, 95, x0 + 18, 112), seal_l, "Spacer", "solid", 0, 1,
            outline=False)
    poly(rect(90, 110, 108, 145), frame_l, "Glazing bead")
    for x0, y0 in ((104, 110), (164, 110), (84, 14), (194, 14)):
        cut(rect(x0, y0, x0 + 6, y0 + 10), seal_l, "Gasket", "solid", 0, 1,
            outline=False)
    # a break line across the glass, where the drawing stops
    poly([(50, 680), (120, 680), (135, 710), (150, 660), (165, 690),
          (240, 690)], seal_l, "Break line", closed=False)

    # outside: the seal, the perimeter insulation and the drainage
    poly([(80, -40), (200, -40), (200, -465)], membrane_l, "Waterproofing",
         closed=False)
    cut(rect(200, -900, 320, -40), insul_l, "Perimeter insulation", "lines",
        45, 20)
    cut(rect(-1200, -465, 200, -365), insul_l, "Insulation under slab",
        "lines", 45, 20)
    poly(rect(360, -170, 500, -40), metal_l, "Drainage channel")
    for x in range(372, 500, 16):
        poly([(x, -46), (x + 8, -46), (x + 8, -40), (x, -40)], metal_l,
             "Grating bar")
    cut(rect(510, -80, 1700, -40), stone_l, "Terrace slab", "lines", 60, 12)
    poly([(950, -80), (950, -40)], stone_l, "Joint", closed=False)
    cut(rect(510, -130, 1700, -80), gravel_l, "Grit bed", "dots", 0, 10)
    cut([(320, -500), (1700, -500), (1700, -130), (510, -130), (510, -40),
         (500, -40), (500, -170), (360, -170), (360, -40), (320, -40)],
        gravel_l, "Gravel", "dots", 0, 28)
    cut([(200, -1000), (1700, -1000), (1700, -500), (320, -500),
         (320, -900), (200, -900)], earth_l, "Earth", "lines", 135, 40)
    cut(rect(-1200, -1000, 200, -465), earth_l, "Earth", "lines", 135, 40)

    # headings and a few dimensions, ticked as architects tick them, where
    # the hatching leaves them legible
    from blackbyrd3d.core.dimension import DimensionShape
    from blackbyrd3d.core.text import TextShape
    note_l = _layer(scene, "Annotation", (0.90, 0.90, 0.92))
    dim_l = _layer(scene, "Dimensions", (0.90, 0.90, 0.92))
    dim_style = dict(text_height=24, arrow="tick", arrow_size=14,
                     decimals=0, trailing_zeros=False)
    for p1, p2, y, name in (
            ((200, -40), (510, -40), 300, "Facade to terrace"),
            ((200, -380), (320, -380), -360, "Perimeter insulation"),
            ((360, -40), (500, -40), 150, "Drainage channel")):
        scene.add(DimensionShape((*p1, 0), (*p2, 0), (0, y, 0),
                                 direction=(1, 0, 0), **dim_style),
                  name=f"{name} dimension", layer_id=dim_l)
    # the build-up on each side: a leader down through its layers, a dot
    # on each, and the layers listed above it top to bottom
    size, gap = 24.0, 40.0

    def dot(x, y):
        region = geo.planar_face(geo.make_circle((x, y, 0), 8))
        scene.add(HatchShape(region, "solid", angle=0, spacing=1,
                             xdir=(1, 0, 0)), name="Leader dot",
                  layer_id=note_l)

    def build_up(x, ys, lines, text_x, base_y, line_to, align):
        poly([(x, min(ys)), (x, base_y), (line_to, base_y)], note_l,
             "Leader", closed=False)
        for y in ys:
            dot(x, y)
        for i, line in enumerate(reversed(lines)):
            scene.add(TextShape(line, size, origin=(text_x,
                                                    base_y + 12 + i * gap, 0),
                                alignment=align),
                      name=line, layer_id=note_l)

    build_up(-480, [-7, -45, -95, -240, -415],
             ["Parquet 15 mm", "Cement screed 60 mm",
              "Impact sound insulation 40 mm",
              "Reinforced concrete slab 250 mm",
              "Insulation under slab XPS 100 mm"], -620, 250, -620, "left")
    build_up(840, [-60, -105, -320],
             ["Terrace slab 40 mm", "Grit bed 50 mm", "Gravel 16/32"],
             1060, 150, 1060, "right")
    for label, x, align in (("INSIDE", -620, "left"),
                            ("OUTSIDE", 1060, "right")):
        scene.add(TextShape(label, 48, origin=(x, 590, 0), alignment=align),
                  name=label, layer_id=note_l)


def _stool(scene, geo, wood, fabric, origin, turn, n):
    """One stool: a cushion on a plywood board, two rails crossing in a
    halving joint under it, and four splayed, tapered legs at their ends."""
    parts = []
    seat_h, board_t, cushion_t = 450.0, 18.0, 62.0
    r_seat = 170.0
    rail_h, rail_w, reach = 44.0, 28.0, 118.0
    z_board = seat_h - cushion_t - board_t
    z_rail = z_board - rail_h
    cushion = geo.make_cylinder((0, 0, z_board + board_t), r_seat, cushion_t)
    try:
        cushion = geo.fillet_edges(cushion, 12)
    except Exception:                                   # noqa: BLE001
        pass
    parts.append(("Cushion", cushion, fabric))
    parts.append(("Board", geo.make_cylinder((0, 0, z_board), r_seat - 6,
                                             board_t), wood))
    half = rail_w / 2
    rail_x = geo.make_box((-reach, -half, z_rail), 2 * reach, rail_w, rail_h)
    rail_y = geo.make_box((-half, -reach, z_rail), rail_w, 2 * reach, rail_h)
    # the halving: each rail gives up half its depth where they cross
    rail_x = geo.boolean_difference(rail_x, geo.make_box(
        (-half, -half - 1, z_rail - 1), rail_w, rail_w + 2, rail_h / 2 + 1))
    rail_y = geo.boolean_difference(rail_y, geo.make_box(
        (-half - 1, -half, z_rail + rail_h / 2), rail_w + 2, rail_w,
        rail_h / 2 + 1))
    parts.append(("Rail A", rail_x, wood))
    parts.append(("Rail B", rail_y, wood))
    splay = 80.0
    for i in range(4):
        a = math.pi / 2 * i
        c, s = math.cos(a), math.sin(a)

        def ring(r, zz, along, across):
            pts = [(r + dx, dy) for dx, dy in (
                (-along, -across), (along, -across), (along, across),
                (-along, across))]
            return geo.make_polyline(
                [(x * c - y * s, x * s + y * c, zz) for x, y in pts],
                closed=True)
        top = ring(reach + 24, z_board, 24, half + 6)
        foot = ring(reach + 24 + splay, 0.0, 16, 15)
        parts.append((f"Leg {i + 1}", geo.loft([foot, top], solid=True),
                      wood))
    ids = []
    for name, shape, layer in parts:
        shape = geo.rotate(shape, (0, 0, 0), (0, 0, 1), turn)
        shape = geo.translate(shape, origin)
        ids.append(scene.add(shape, name=f"{name} {n}", layer_id=layer).id)
    return ids


def build_stool(scene, geo):
    """Two oak stools with upholstered seats, and a workshop drawing of one
    on an A3 sheet."""
    from blackbyrd3d.core.layout import DetailView, Layout
    scene.units = "mm"
    wood = _layer(scene, "Oak", (0.78, 0.56, 0.34))
    fabric = _layer(scene, "Fabric", (0.80, 0.77, 0.73))
    first = _stool(scene, geo, wood, fabric, (0, 0, 0), 20.0, 1)
    second = _stool(scene, geo, wood, fabric, (430, -300, 0), 5.0, 2)

    lay = Layout(name="Workshop drawing", paper_w=420.0, paper_h=297.0)
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for oid in first:
        b = geo.bbox(scene.get(oid).shape)
        lo = [min(a, v) for a, v in zip(lo, b[0])]
        hi = [max(a, v) for a, v in zip(hi, b[1])]
    target = [(a + b) / 2 for a, b in zip(lo, hi)]
    views = (
        (math.radians(-90), 0.0, 20, 45, 180, 225),
        (math.radians(-90), math.radians(89.9), 210, 150, 190, 120),
    )
    for az, el, x, y, w, h in views:
        lay.details.append(DetailView(
            x=x, y=y, w=w, h=h, azimuth=az, elevation=el,
            target=list(target), scale_denom=5.0, display_mode="hidden",
            hidden_objects=list(second)))
    both = scene.bbox()
    lay.details.append(DetailView(
        x=210, y=45, w=95, h=95, azimuth=math.radians(-60),
        elevation=math.radians(22),
        target=[(a + b) / 2 for a, b in zip(*both)], perspective=True,
        perspective_distance=2300.0, display_mode="shaded",
        show_border=False))
    lay.title_block = {"template": "standard", "fields": {
        "project": "Example", "title": "Stool with crossed rails",
        "author": "Blackbyrd3D"}}
    scene.layouts.append(lay)


def build_cabin(scene, geo):
    """A small cabin in metres: gabled walls, framed and glazed windows,
    doors, a plan and elevation sheet, and a clipping plane that opens the
    model up in the perspective view."""
    from blackbyrd3d.core.layout import DetailView, Layout
    scene.units = "m"
    walls_l = _layer(scene, "Walls", (0.88, 0.86, 0.82))
    roof_l = _layer(scene, "Roof", (0.42, 0.24, 0.2))
    timber_l = _layer(scene, "Timber", (0.62, 0.45, 0.28))
    frame_l = _layer(scene, "Frames", (0.22, 0.23, 0.25))
    glass_l = _layer(scene, "Glass", (0.62, 0.78, 0.88))
    door_l = _layer(scene, "Doors", (0.55, 0.36, 0.22))
    w, d, h, t, rise = 6.0, 4.0, 2.6, 0.25, 1.4
    walls = geo.boolean_difference(
        geo.make_box((0, 0, 0), w, d, h),
        geo.make_box((t, t, 0), w - 2 * t, d - 2 * t, h))
    # the partition stops under the ceiling
    walls = geo.boolean_union(walls, geo.make_box((3.2, t, 0), t / 2,
                                                  d - 2 * t, h - 0.2))
    for x in (0.0, w - t):
        tri = geo.make_polyline([(x, 0, h), (x, d, h), (x, d / 2, h + rise)],
                                closed=True)
        walls = geo.boolean_union(walls, geo.extrude(tri, (1, 0, 0), t,
                                                     cap=True))
    # (corner, size, the direction the wall runs)
    windows = (((3.8, 0, 0.9), (1.6, t, 1.2), "x"),
               ((w - t, 1.2, 0.9), (t, 1.6, 1.2), "y"),
               ((0, 1.4, 0.9), (t, 1.2, 1.2), "y"),
               ((1.125, d - t, 1.0), (1.2, t, 1.1), "x"),
               ((w - t, d / 2 - 0.3, h + 0.25), (t, 0.6, 0.6), "y"))
    doors = (((1.0, 0, 0), (1.0, t, 2.1), "x"),
             ((3.2, 1.4, 0), (t / 2, 0.9, 2.05), "y"))
    for (x, y, z), (sx, sy, sz), run in windows + doors:
        if run == "x":
            cut = geo.make_box((x, y - 0.01, z), sx, sy + 0.02, sz)
        else:
            cut = geo.make_box((x - 0.01, y, z), sx + 0.02, sy, sz)
        walls = geo.boolean_difference(walls, cut)
    walls = geo.boolean_union(walls, geo.make_box(
        (-0.2, -0.2, -0.2), w + 0.4, d + 0.4, 0.2))
    walls = geo.boolean_union(walls, geo.make_box(
        (t, t, h - 0.2), w - 2 * t, d - 2 * t, 0.2))
    scene.add(walls, name="Walls and floors", layer_id=walls_l)

    def frame(corner, size, run, depth=0.07, bar=0.06):
        x, y, z = corner
        sx, sy, sz = size
        if run == "x":
            y0 = y + (sy - depth) / 2
            box = geo.make_box((x, y0, z), sx, depth, sz)
            hole = geo.make_box((x + bar, y0 - 0.01, z + bar),
                                sx - 2 * bar, depth + 0.02, sz - 2 * bar)
            pane = geo.make_box((x + bar, y0 + depth / 2 - 0.004, z + bar),
                                sx - 2 * bar, 0.008, sz - 2 * bar)
        else:
            x0 = x + (sx - depth) / 2
            box = geo.make_box((x0, y, z), depth, sy, sz)
            hole = geo.make_box((x0 - 0.01, y + bar, z + bar),
                                depth + 0.02, sy - 2 * bar, sz - 2 * bar)
            pane = geo.make_box((x0 + depth / 2 - 0.004, y + bar, z + bar),
                                0.008, sy - 2 * bar, sz - 2 * bar)
        return geo.boolean_difference(box, hole), pane

    for i, (corner, size, run) in enumerate(windows, 1):
        fr, pane = frame(corner, size, run)
        scene.add(fr, name=f"Window frame {i}", layer_id=frame_l)
        glass = scene.add(pane, name=f"Glass {i}", layer_id=glass_l)
        glass.material = {"metallic": 0.0, "roughness": 0.05,
                          "opacity": 0.35}
    for i, (corner, size, run) in enumerate(doors, 1):
        x, y, z = corner
        sx, sy, sz = size
        depth = min(0.07, (sy if run == "x" else sx) - 0.02)
        fr, _pane = frame(corner, size, run, depth=depth, bar=0.05)
        scene.add(fr, name=f"Door frame {i}", layer_id=frame_l)
        # the leaf fills the frame's opening, clear of its sill
        if run == "x":
            leaf = geo.make_box((x + 0.05, y + (sy - 0.04) / 2, z + 0.05),
                                sx - 0.1, 0.04, sz - 0.1)
        else:
            leaf = geo.make_box((x + (sx - 0.04) / 2, y + 0.05, z + 0.05),
                                0.04, sy - 0.1, sz - 0.1)
        scene.add(leaf, name=f"Door {i}", layer_id=door_l)

    # the ridge purlin, its top clear of the roof slopes
    pw, ph = 0.16, 0.24
    top = h + rise - pw / 2 * rise / (d / 2)
    scene.add(geo.make_box((-0.3, d / 2 - pw / 2, top - ph), w + 0.6, pw,
                           ph), name="Ridge purlin", layer_id=timber_l)
    eave = h - 0.4 * rise / (d / 2)
    pitch = geo.make_polyline([(-0.3, -0.4, eave), (w + 0.3, -0.4, eave),
                               (w + 0.3, d / 2, h + rise),
                               (-0.3, d / 2, h + rise)], closed=True)
    half = geo.extrude(pitch, (0, 0, 1), 0.15, cap=True)
    scene.add(half, name="Roof south", layer_id=roof_l)
    scene.add(geo.mirror(half, (0, d / 2, 0), (0, 1, 0)),
              name="Roof north", layer_id=roof_l)

    lay = Layout(name="Plan and elevation", paper_w=420.0, paper_h=297.0)
    bounds = scene.bbox()
    target = [(a + b) / 2 for a, b in zip(*bounds)]
    section = 1.2 - target[2]
    for x, w_, el, cut in ((25, 200, math.radians(89.9), section),
                           (235, 165, 0.0, None)):
        lay.details.append(DetailView(
            x=x, y=110, w=w_, h=160, azimuth=math.radians(-90), elevation=el,
            target=list(target), scale_denom=0.05, display_mode="hidden",
            section_offset=cut))
    lay.title_block = {"template": "standard", "fields": {
        "project": "Example", "title": "Garden cabin",
        "author": "Blackbyrd3D"}}
    scene.layouts.append(lay)

    # Made after the sheet, which frames the model's bounds. A section
    # through the cabin, taking away its east end, facing the camera, in
    # the perspective view alone: the sheet keeps its own cuts.
    # Its frame stands beside the cabin, in the plane of the cut, so it
    # shows without hiding the section.
    cut_x = 4.4
    y0, y1, z0, z1 = d + 0.8, d + 3.0, 1.6, 3.8
    plane = geo.planar_face(geo.make_polyline(
        [(cut_x, y0, z0), (cut_x, y1, z0), (cut_x, y1, z1), (cut_x, y0, z1)],
        closed=True))
    # the normal points at the half it takes away
    if geo.face_normal(next(iter(geo.faces_of(plane))))[0] < 0:
        plane = geo.mirror(plane, (cut_x, 0, 0), (1, 0, 0))
    clip_l = _layer(scene, "Section", (0.62, 0.42, 0.85))
    section = scene.add(plane, name="Section", layer_id=clip_l)
    scene.update(section.id, clip_plane={"enabled": True,
                                         "on_in": ["perspective"]})


def build_urban(scene, geo):
    """A generic city quarter in metres: three by three blocks between
    streets, perimeter buildings round courtyards, a tower, and a park with
    trees and a pond in the middle. Each layer has its own colour, which
    plaster colour shows. The trees are instances of one block, each
    scaled to its own size."""
    import uuid
    import random
    scene.units = "m"
    rnd = random.Random(7)
    street_l = _layer(scene, "Streets", (0.72, 0.72, 0.73))
    walk_l = _layer(scene, "Pavement", (0.86, 0.86, 0.85))
    build_l = _layer(scene, "Buildings", (1.0, 1.0, 1.0))
    lawn_l = _layer(scene, "Lawn", (0.55, 0.70, 0.42))
    tree_l = _layer(scene, "Trees", (0.33, 0.52, 0.30))
    water_l = _layer(scene, "Water", (0.45, 0.64, 0.80))

    block, street, n = 44.0, 14.0, 3
    span = n * block + (n + 1) * street
    scene.add(geo.make_box((0, 0, -0.4), span, span, 0.4),
              name="Streets", layer_id=street_l)
    buildings, walks, trees = [], [], []
    # a tree of size 1, standing on its base point
    tree_id = uuid.uuid4().hex[:8]
    scene.block_defs[tree_id] = {"name": "Tree", "shapes": [
        geo.make_cylinder((0, 0, 0), 0.25, 2.2),
        geo.make_sphere((0, 0, 3.8), 1.9)]}

    def tree(x, y, size):
        trees.append((x, y, size))

    for i in range(n):
        for j in range(n):
            x0 = street + i * (block + street)
            y0 = street + j * (block + street)
            walks.append(geo.make_box((x0, y0, 0), block, block, 0.15))
            if (i, j) == (1, 1):
                scene.add(geo.make_box((x0 + 3, y0 + 3, 0.15), block - 6,
                                       block - 6, 0.1),
                          name="Park", layer_id=lawn_l)
                scene.add(geo.make_cylinder((x0 + 27, y0 + 17, 0.15), 7,
                                            0.12),
                          name="Pond", layer_id=water_l)
                for _ in range(16):
                    while True:
                        tx = x0 + rnd.uniform(6, block - 6)
                        ty = y0 + rnd.uniform(6, block - 6)
                        if math.hypot(tx - x0 - 27, ty - y0 - 17) > 10:
                            break
                    tree(tx, ty, rnd.uniform(0.8, 1.25))
                continue
            if (i, j) == (2, 2):
                buildings.append(geo.make_box((x0 + 10, y0 + 10, 0.15), 22,
                                              22, 62))
                buildings.append(geo.make_box((x0 + 4, y0 + 4, 0.15), 36,
                                              36, 7))
                continue
            # a perimeter block: four wings round a courtyard, each its own
            # height
            d = 12.0
            wings = ((x0 + 2, y0 + 2, block - 4, d),
                     (x0 + 2, y0 + block - 2 - d, block - 4, d),
                     (x0 + 2, y0 + 2 + d, d, block - 4 - 2 * d),
                     (x0 + block - 2 - d, y0 + 2 + d, d, block - 4 - 2 * d))
            for wx, wy, ww, wd in wings:
                h = rnd.choice((12.5, 15.5, 18.5, 21.5))
                buildings.append(geo.make_box((wx, wy, 0.15), ww, wd, h))
            for _ in range(3):
                tree(x0 + rnd.uniform(18, block - 18),
                     y0 + rnd.uniform(18, block - 18), rnd.uniform(0.7, 1.0))
    # street trees along the avenues
    for k in range(n + 1):
        for t in range(10):
            along = 6 + t * (span - 12) / 9
            tree(street / 2 + k * (block + street), along, 0.8)
    scene.add(geo.make_compound(walks), name="Pavement", layer_id=walk_l)
    scene.add(geo.make_compound(buildings), name="Buildings",
              layer_id=build_l)
    shape = geo.make_compound(scene.block_defs[tree_id]["shapes"])
    for k, (x, y, size) in enumerate(trees, 1):
        placed = geo.translate(geo.scale(shape, (0, 0, 0), size),
                               (x, y, 0.15))
        inst = scene.add(placed, name=f"Tree {k:02d}", layer_id=tree_l)
        scene.update(inst.id, block_id=tree_id)


# azimuth and elevation in degrees, where the standard view will not do
CAMERAS = {"cabin": (-28.0, 20.0), "urban": (-40.0, 32.0)}
# how much closer than Zoom Extents
ZOOM = {"urban": 0.74}
# an exact frame where Zoom Extents will not do, for a parallel view: the
# left and right edge in view and the bottom edge; the height follows from
# the pane's shape
FRAME = {"detail": (-680.0, 1120.0, -482.0)}
# the height the camera aims at instead of the middle of the bounds, so a
# tall part does not push the rest down the picture
AIM_Z = {"urban": -24.0}
# shown without the construction grid
NO_GRID = {"detail", "stool", "urban"}

EXAMPLES = (
    ("detail", build_detail, "top", "shaded"),
    ("stool", build_stool, "perspective", "shaded"),
    ("cabin", build_cabin, "perspective", "shaded"),
    ("urban", build_urban, "perspective", "plastercolor"),
)


def _wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _png(img) -> bytes:
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def _shot(window):
    """What is on screen, overlays included: grab() leaves out what is
    painted over the GL panes."""
    from PySide6.QtGui import QCursor
    QCursor.setPos(window.screen().geometry().bottomRight())
    window.selection.clear()
    _wait(400)
    return window.screen().grabWindow(window.winId()).toImage()


def _sheet_shot(window, name):
    """The first sheet, when there is one."""
    if not window.scene.layouts:
        return
    window.switch_space(window.scene.layouts[0].id)
    _wait(2500)
    _shot(window).save(os.path.join(SHOTS_DIR, f"{name}-sheet.png"))
    window.switch_space("model")
    _wait(500)


def main():
    app = QApplication(sys.argv)
    import blackbyrd3d.commands  # noqa: F401
    from blackbyrd3d import fileio
    from blackbyrd3d.app import MainWindow
    from blackbyrd3d.core import geometry as geo
    from blackbyrd3d.ui import theme
    app.setStyleSheet(theme.stylesheet())

    os.makedirs(EXAMPLES_DIR, exist_ok=True)
    os.makedirs(SHOTS_DIR, exist_ok=True)
    window = MainWindow()
    window.resize(1440, 900)
    window.show()
    _wait(800)
    args = sys.argv[1:]
    shots_only = "--shots-only" in args
    reframe = "--reframe" in args
    only = args[args.index("--only") + 1] if "--only" in args else None
    for name, build, view, mode in EXAMPLES:
        if only and name != only:
            continue
        path = os.path.join(EXAMPLES_DIR, f"{name}.byrd")
        if shots_only:
            window.start_new("mm")
            fileio.import_file(window.scene, path, replace=True)
            window.scene.notify()
            window.show_perspective_alone()
            vp = window.viewport
            vp.set_view(view)           # its name; the camera comes after
            if not window.apply_view_settings():
                vp.set_view(view)
                vp.zoom_extents()
            _wait(1500)
            window.ctx.current_path = path
            window.mark_saved()
            _wait(300)
            _shot(window).save(os.path.join(SHOTS_DIR, f"{name}.png"))
            _sheet_shot(window, name)
            print(f"{name}: screenshot of {path}")
            continue
        window.start_new("mm")
        if reframe:
            # the drawing as someone left it; only its view is set again
            fileio.import_file(window.scene, path, replace=True)
        else:
            build(window.scene, geo)
        window.scene.notify()
        window.show_perspective_alone()
        vp = window.viewport
        vp.set_view(view)
        if name in CAMERAS:
            az, el = CAMERAS[name]
            vp.camera.azimuth = math.radians(az)
            vp.camera.elevation = math.radians(el)
        vp.set_display_mode(mode)
        if name in NO_GRID:
            vp.grid_visible = False
            vp.grid_axes_visible = False
        vp.zoom_extents()
        _wait(1500)
        land = getattr(vp, "land_flight", None)
        if land is not None:
            land()
        if name in ZOOM:
            vp.camera.distance *= ZOOM[name]
        if name in AIM_Z:
            vp.camera.target[2] = AIM_Z[name]
        if name in FRAME:
            left, right, bottom = FRAME[name]
            half = (right - left) / 2 * vp.height() / max(vp.width(), 1)
            vp.camera.target[0] = (left + right) / 2
            vp.camera.target[1] = bottom + half
            vp.camera.distance = half / math.tan(
                math.radians(vp.camera.fov) / 2)
        vp.update()
        _wait(500)
        thumb = vp.grabFramebuffer().scaled(
            512, 512, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        window.store_view_settings()
        fileio.export_file(window.scene, path, thumbnail=_png(thumb))
        window.ctx.current_path = path
        window.mark_saved()
        _wait(300)
        _shot(window).save(os.path.join(SHOTS_DIR, f"{name}.png"))
        _sheet_shot(window, name)
        print(f"{name}: {len(window.scene.all())} objects -> {path}")
    window.close()


if __name__ == "__main__":
    main()
