"""Text as curves, via Qt font outlines."""

from __future__ import annotations

import functools
import threading

from .text_object import TextShape


@functools.cache
def _metrics(font_family: str):
    """`font_family`'s metrics at 2048 pixels, enough that rounding them is
    far below anything drawn."""
    from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication

    if QGuiApplication.instance() is None:      # headless/scripting use
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        _metrics._app = QGuiApplication([])
    font = QFont(font_family)
    font.setPixelSize(2048)
    return QFontMetricsF(font)


def cap_height_ratio(font_family: str = "sans") -> float:
    """A font's capital height for each unit of its size, its em: 0.714 for
    Noto Sans. The size has room for ascenders, descenders and accents too,
    so text whose capitals are `h` tall is set in a font `h / ratio` big."""
    return _metrics(font_family).capHeight() / 2048


def text_advance(text: str, font_family: str = "sans") -> float:
    """How far a line of `text` runs in a font, for each unit of its size."""
    return _metrics(font_family).horizontalAdvance(text) / 2048


def _font(font_family: str, bold: bool, font_style: str):
    from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

    if QGuiApplication.instance() is None:      # headless/scripting use
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        text_path._app = QGuiApplication([])
    if font_style:
        font = QFontDatabase.font(font_family, font_style, 12)
    else:
        font = QFont(font_family)
        font.setBold(bold)
    # Use enough resolution to keep font metric rounding below model precision.
    font.setPixelSize(2048)
    return font


def text_path(text: str, height: float, font_family: str = "sans",
              bold: bool = False, *, font_style: str = "",
              alignment: str = "left"):
    """Font outlines in model units, with the first baseline at the origin.

    The returned Qt path uses downward-positive Y. Each line aligns its font
    advance to the origin, and ``height`` is the font's capital-letter height.
    Rendering and modelling can share these exact outlines and metrics.
    """
    import math
    from PySide6.QtGui import QFontMetricsF, QPainterPath, QTransform
    from . import geometry

    if not text.strip():
        raise geometry.GeometryError("Empty text")
    if not math.isfinite(height) or height <= 0:
        raise geometry.GeometryError("Text height must be positive and finite")
    if alignment not in ("left", "center", "right"):
        raise geometry.GeometryError("Text alignment must be left, center or right")
    font = _font(font_family, bold, font_style)
    metrics = QFontMetricsF(font)
    cap_height = metrics.capHeight()
    if cap_height <= 0:
        raise geometry.GeometryError("Font has no capital-letter height")

    path = QPainterPath()
    factor = {"left": 0.0, "center": 0.5, "right": 1.0}[alignment]
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for row, line in enumerate(lines):
        path.addText(-factor * metrics.horizontalAdvance(line),
                     row * metrics.lineSpacing(), font, line)
    if path.isEmpty():
        raise geometry.GeometryError("Font produced no outlines")
    scale = float(height) / cap_height
    return QTransform().scale(scale, scale).map(path)


def text_curves(text: str, height: float, font_family: str = "sans",
                bold: bool = False, *, font_style: str = "",
                alignment: str = "left") -> list:
    """Closed line/Bezier glyph contours on XY, preserving separate counters.

    The first baseline is at the origin, positive Y points up, and subsequent
    lines extend down. ``height`` specifies the font's capital-letter height.
    """
    from . import geometry

    path = text_path(text, height, font_family, bold,
                     font_style=font_style, alignment=alignment)
    curves = _wires(_elements(path))
    if not curves:
        raise geometry.GeometryError("No text outlines produced")
    return curves


def _elements(path) -> list:
    """A Qt path's elements as plain (kind, x, y) tuples, kind being 0
    move, 1 line, 2 the first point of a cubic and 3 the rest of it."""
    out = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        out.append((element.type.value, element.x, element.y))
    return out


def _wires(elements) -> list:
    """Closed wires on XY from path elements whose Y points down."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.Geom import Geom_BezierCurve
    from OCP.Precision import Precision
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.gp import gp_Pnt
    from . import geometry

    tolerance = Precision.Confusion_s()

    curves = []
    wire = None
    start = current = None

    def point(index):
        _kind, x, y = elements[index]
        return gp_Pnt(x, -y, 0.0)

    def finish_contour():
        if wire is None or not wire.IsDone():
            return
        if not current.IsEqual(start, tolerance):
            wire.Add(BRepBuilderAPI_MakeEdge(current, start).Edge())
        if not wire.IsDone():
            raise geometry.GeometryError("Unable to close a text outline")
        curves.append(wire.Wire())

    index = 0
    while index < len(elements):
        kind = elements[index][0]
        if kind == 0:
            finish_contour()
            wire = BRepBuilderAPI_MakeWire()
            start = current = point(index)
        elif kind == 1:
            end = point(index)
            if not current.IsEqual(end, tolerance):
                wire.Add(BRepBuilderAPI_MakeEdge(current, end).Edge())
            current = end
        elif kind == 2:
            poles = TColgp_Array1OfPnt(1, 4)
            poles.SetValue(1, current)
            for offset in range(3):
                poles.SetValue(offset + 2, point(index + offset))
            wire.Add(BRepBuilderAPI_MakeEdge(Geom_BezierCurve(poles)).Edge())
            current = point(index + 2)
            index += 2
        index += 1
    finish_contour()
    return curves


# Text is drawn the way a desktop draws it: each glyph of a font is filled
# and meshed once, and a line of text is copies of those set where the
# layout puts them. Keyed by the font a glyph came from and its index.
_glyph_lock = threading.Lock()
_glyph_outlines: dict = {}
_glyph_meshes: dict = {}
# How closely a glyph's mesh follows its curves, in the 2048 pixel em.
GLYPH_DEFLECTION = 4.0


def glyph_layout(text: str, font_family: str = "sans", bold: bool = False, *,
                 font_style: str = "", alignment: str = "left"):
    """(cap height, placements) for `text` as `text_path` sets it, before
    scaling: each placement is (glyph key, x, y), the glyph's origin in
    the font's pixels with Y down. None when the glyphs would not add up
    to the same outlines, as they do not for a synthesised bold."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QFontMetricsF, QPainterPath, QTextLayout

    font = _font(font_family, bold, font_style)
    metrics = QFontMetricsF(font)
    factor = {"left": 0.0, "center": 0.5, "right": 1.0}.get(alignment)
    if factor is None or metrics.capHeight() <= 0:
        return None
    reference = QPainterPath()
    placements = []
    ink = QRectF()
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for row, line in enumerate(lines):
        x0 = -factor * metrics.horizontalAdvance(line)
        y0 = row * metrics.lineSpacing()
        reference.addText(x0, y0, font, line)
        layout = QTextLayout(line, font)
        layout.beginLayout()
        laid = layout.createLine()
        layout.endLayout()
        if not laid.isValid():
            continue
        for run in laid.glyphRuns():
            raw = run.rawFont()
            face = (raw.familyName(), raw.styleName(), raw.weight(),
                    raw.style().value, raw.pixelSize())
            for index, at in zip(run.glyphIndexes(), run.positions()):
                key = (face, index)
                held = _glyph_outlines.get(key)
                if held is None:
                    path = raw.pathForGlyph(index)
                    held = (_elements(path), path.boundingRect())
                    _glyph_outlines[key] = held
                x, y = x0 + at.x(), y0 + at.y() - laid.ascent()
                if not held[1].isEmpty():
                    ink = ink.united(held[1].translated(x, y))
                placements.append((key, x, y))
    want = reference.boundingRect()
    if not all(abs(a - b) < 0.5 for a, b in zip(
            (ink.left(), ink.top(), ink.right(), ink.bottom()),
            (want.left(), want.top(), want.right(), want.bottom()))):
        return None
    return metrics.capHeight(), placements


def glyph_mesh(key):
    """A glyph's filled mesh in the font's pixels, Y up: (corners (N, 2),
    which way each corner's face looks along Z (N,), triangles (M, 3),
    the region each triangle fills (M,), (low, high) corners of its
    outline's box or None for a blank). None if its outline does not
    close into regions."""
    held = _glyph_meshes.get(key, _glyph_lock)
    if held is not _glyph_lock:
        return held
    built = _mesh_glyph(_glyph_outlines[key][0])
    with _glyph_lock:
        _glyph_meshes[key] = built
    return built


def _mesh_glyph(outline):
    import numpy as np
    from . import geometry
    from .tessellate import tessellate

    wires = _wires(outline)
    if not wires:
        return (np.zeros((0, 2)), np.zeros(0), np.zeros((0, 3), np.uint32),
                np.zeros(0, np.int32), None)
    try:
        faces = geometry.planar_regions(wires)
    except Exception:                                  # noqa: BLE001
        return None
    if not faces:
        return None
    mesh = tessellate(geometry.make_compound(faces), GLYPH_DEFLECTION)
    if not len(mesh.triangles):
        return None
    lo, hi = geometry.bbox(geometry.make_compound(wires))
    return (np.asarray(mesh.vertices, float)[:, :2],
            np.sign(np.asarray(mesh.normals, float)[:, 2]),
            np.asarray(mesh.triangles, np.uint32),
            np.asarray(mesh.face_of_triangle, np.int32),
            (np.asarray(lo[:2], float), np.asarray(hi[:2], float)))
