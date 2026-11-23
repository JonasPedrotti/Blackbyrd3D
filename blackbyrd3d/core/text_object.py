"""Editable model lettering with cached, portable outline geometry."""

from __future__ import annotations

import json
import math
import struct

import numpy as np
from OCP.TopoDS import TopoDS_Compound

from . import geometry, occ


TEXT_TAG = b"STXT\x01"
# The background reaches this far past the lettering, in cap heights.
DEFAULT_MARGIN = 0.25


class TextShape(TopoDS_Compound):
    """One selectable text label, also usable by ordinary BREP operations.

    Typography edits return a new object. The placement frame retains rotation,
    mirroring and stretching; its Y axis has unit length so ``height`` remains
    the physical cap height after scaling. Cached contours let saved labels
    display identically even on a machine without the original font.
    """

    def __init__(self, text: str, height: float, font_family: str = "sans", *,
                 font_style: str = "", alignment: str = "left",
                 origin=(0., 0., 0.)):
        from .text import glyph_layout, text_curves

        frame = np.eye(4)
        frame[:3, 3] = origin
        curves = text_curves(text, height, font_family,
                             font_style=font_style, alignment=alignment)
        brep = geometry.apply_matrix(geometry.make_compound(curves), frame)
        self._initialize(text, height, font_family, font_style, alignment,
                         frame, brep)
        self._glyphs = glyph_layout(text, font_family, font_style=font_style,
                                    alignment=alignment)
        self._glyphs_match = True

    def _initialize(self, text, height, font_family, font_style, alignment,
                    frame, brep, background=False, margin=DEFAULT_MARGIN):
        super().__init__()
        self.TShape(brep.TShape())
        self.Location(brep.Location())
        self.Orientation(brep.Orientation())
        self._text = str(text)
        self._height = float(height)
        self._font_family = str(font_family)
        self._font_style = str(font_style)
        self._alignment = str(alignment)
        self._frame = tuple(tuple(float(v) for v in row) for row in frame)
        self._brep = brep
        self._background = bool(background)
        self._margin = max(0., float(margin))
        # How the font lays the text out (see text.glyph_layout): unknown
        # until asked for text read from a file, which may have been set
        # in a font this machine does not have.
        self._glyphs = _UNKNOWN
        self._glyphs_match = None
        self._bbox = None

    @classmethod
    def _from_geometry(cls, typography, frame, brep, look=None):
        result = cls.__new__(cls)
        result._initialize(**typography, frame=frame, brep=brep, **(look or {}))
        return result

    def _same_letters(self, other):
        """`other` with this text's lettering: what the font made of it
        does not change by moving it or giving it a background."""
        other._glyphs = self._glyphs
        other._glyphs_match = self._glyphs_match
        if hasattr(self, "_glyph_mesh"):
            other._glyph_mesh = self._glyph_mesh
        return other

    @property
    def text(self):
        return self._text

    @property
    def height(self):
        return self._height

    @property
    def font_family(self):
        return self._font_family

    @property
    def font_style(self):
        return self._font_style

    @property
    def alignment(self):
        return self._alignment

    @property
    def background(self) -> bool:
        """Whether the text sits on a patch of the drawing's own colour,
        hiding what lies behind it."""
        return self._background

    @property
    def margin(self) -> float:
        """How far the background reaches past the lettering on every
        side, as a fraction of the cap height."""
        return self._margin

    def _look(self):
        return dict(background=self._background, margin=self._margin)

    def with_background(self, background=None, margin=None):
        """The same lettering with its background switched or widened."""
        look = self._look()
        if background is not None:
            look["background"] = bool(background)
        if margin is not None:
            look["margin"] = float(margin)
        return self._same_letters(self._from_geometry(
            self._typography(), self._frame, self._brep, look))

    @property
    def origin(self):
        return tuple(row[3] for row in self._frame[:3])

    @property
    def frame(self) -> np.ndarray:
        """The placement axes and origin, independent of the lettering."""
        return np.asarray(self._frame, float)

    @property
    def plane_normal(self):
        """Unit normal of the transformed plane carrying the lettering."""
        frame = np.asarray(self._frame, dtype=float)
        normal = np.cross(frame[:3, 0], frame[:3, 1])
        length = float(np.linalg.norm(normal))
        if not math.isfinite(length) or length < 1e-12:
            raise geometry.GeometryError("Text plane is degenerate")
        return tuple(normal / length)

    def _typography(self):
        return dict(text=self.text, height=self.height,
                    font_family=self.font_family, font_style=self.font_style,
                    alignment=self.alignment)

    def edited(self, **typography):
        """Rebuild lettering at its current placement, preserving prior states."""
        from .text import glyph_layout, text_curves

        values = self._typography()
        unknown = typography.keys() - values.keys()
        if unknown:
            raise TypeError(f"Unknown text property: {', '.join(sorted(unknown))}")
        values.update(typography)
        curves = text_curves(**values)
        brep = geometry.apply_matrix(geometry.make_compound(curves), self._frame)
        result = self._from_geometry(values, self._frame, brep, self._look())
        result._glyphs = glyph_layout(
            values["text"], values["font_family"],
            font_style=values["font_style"], alignment=values["alignment"])
        result._glyphs_match = True
        return result

    def transformed(self, matrix):
        """Transform cached geometry and its typography frame together."""
        matrix = np.asarray(matrix, dtype=float)
        frame = matrix @ np.asarray(self._frame)
        height_scale = float(np.linalg.norm(frame[:3, 1]))
        if not np.isfinite(frame).all() or height_scale < 1e-12:
            raise geometry.GeometryError("Text transform is degenerate")
        if math.isclose(height_scale, 1., rel_tol=1e-12):
            height_scale = 1.
        frame[:3, :3] /= height_scale
        values = self._typography()
        values["height"] *= height_scale
        brep = geometry.apply_matrix(self._brep, matrix)
        result = self._same_letters(
            self._from_geometry(values, frame, brep, self._look()))
        # The shape of the lettering has not changed, only where it is:
        # carry what was worked out from it rather than work it out again,
        # which made dragging text stutter.
        if getattr(self, "_fill", None) is not None:
            result._fill = _carried(self._fill, matrix)
        if hasattr(self, "_frame_box"):
            box = np.c_[self._frame_box, np.ones(len(self._frame_box))]
            result._frame_box = (box @ matrix.T)[:, :3]
        if self._bbox is not None and np.allclose(matrix[:3, :3], np.eye(3)):
            shift = matrix[:3, 3]
            result._bbox = tuple(tuple(float(v) for v in np.add(corner, shift))
                                 for corner in self._bbox)
        return result

    def copy(self):
        return self._same_letters(self._from_geometry(
            self._typography(), self._frame, geometry.copy_shape(self._brep),
            self._look()))

    def bbox(self):
        """World bounds of the outlines, measured once: a move only shifts
        them."""
        if self._bbox is None:
            from OCP.Bnd import Bnd_Box
            box = Bnd_Box()
            occ.bbox_add(self, box)
            if box.IsVoid():
                return ((0, 0, 0), (0, 0, 0))
            xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
            self._bbox = ((xmin, ymin, zmin), (xmax, ymax, zmax))
        return self._bbox

    def _letters(self):
        """(cap height, placements) from the font when its glyphs are the
        ones these outlines were made from, else None."""
        if self._glyphs is _UNKNOWN:
            from PySide6.QtCore import QCoreApplication, QThread
            app = QCoreApplication.instance()
            if app is None or QThread.currentThread() is not app.thread():
                return None
            from .text import glyph_layout
            try:
                self._glyphs = glyph_layout(
                    self._text, self._font_family,
                    font_style=self._font_style, alignment=self._alignment)
            except Exception:                              # noqa: BLE001
                self._glyphs = None
        if self._glyphs is None or self._glyphs_match is False:
            return None
        if self._glyphs_match is None:
            # read from a file: the font here has to draw what was saved
            mesh = self._glyph_px()
            ink = self._outline_box()
            fit = None if mesh is None else self._glyph_box(mesh)
            self._glyphs_match = bool(
                fit is not None and np.allclose(
                    fit, ink, atol=1e-3 * self._height + 1e-6))
            if not self._glyphs_match:
                return None
        return self._glyphs

    def _glyph_px(self):
        """The glyphs' meshes put together, in the font's pixels with Y
        up, or None if a glyph has no fill."""
        if not hasattr(self, "_glyph_mesh"):
            from .text import glyph_mesh
            parts = []
            for key, x, y in self._glyphs[1]:
                part = glyph_mesh(key)
                if part is None:
                    parts = None
                    break
                parts.append((part, x, -y))
            self._glyph_mesh = None if parts is None else _joined(parts)
        return self._glyph_mesh

    def _glyph_box(self, mesh):
        """The outlines' local (low, high) on XY from the glyph boxes."""
        lo, hi = mesh[4]
        if lo is None:
            return None
        s = self._height / self._glyphs[0]
        return np.array([lo * s, hi * s])

    def display_mesh(self):
        """What is drawn of the text, built from the font's glyphs as a
        desktop draws text, or None to mesh the outlines instead."""
        if self._letters() is None:
            return None
        joined = self._glyph_px()
        if joined is None:
            return None
        from .tessellate import _CURVATURE, DisplayMesh
        points, facing, triangles, regions, _box = joined
        frame = np.asarray(self._frame, dtype=float)
        s = self._height / self._glyphs[0]
        world = (points * s) @ frame[:3, :2].T + frame[:3, 3]
        normal = np.cross(frame[:3, 0], frame[:3, 1])
        normal /= np.linalg.norm(normal) or 1.
        mesh = DisplayMesh()
        if len(triangles):
            mesh.place(vertices=world)
            mesh.normals = (facing[:, None] * normal).astype(np.float32)
            mesh.triangles = triangles
            mesh.curvature = np.zeros(len(world), np.float32)
            mesh.has_curvature = _CURVATURE
            mesh.face_of_triangle = regions
        return mesh

    def _outline_box(self):
        """The outlines' (low, high) on the text's own plane."""
        frame = np.asarray(self._frame, dtype=float)
        local = geometry.apply_matrix(self._brep, np.linalg.inv(frame))
        lo, hi = geometry.bbox(local)
        return np.array([lo[:2], hi[:2]], float)

    def _local_box(self):
        mesh = self._glyph_px() if self._letters() is not None else None
        fit = None if mesh is None else self._glyph_box(mesh)
        (lo, hi) = fit if fit is not None else self._outline_box()
        grow = self._margin * self._height if self._background else 0.
        x0, y0 = lo[0] - grow, lo[1] - grow
        x1, y1 = hi[0] + grow, hi[1] + grow
        return np.array([
            [x0, y0, 0., 1.], [x1, y0, 0., 1.],
            [x1, y1, 0., 1.], [x0, y1, 0., 1.],
        ])

    def frame_box(self):
        """The four corners of the oriented visible bounds in world space,
        its background's when it has one: the ones the text snaps to, the
        area a click picks it by, and where its selection frame is drawn."""
        if not hasattr(self, "_frame_box"):
            frame = np.asarray(self._frame, dtype=float)
            self._frame_box = (self._local_box() @ frame.T)[:, :3]
        return self._frame_box

    def snap_points(self):
        """Insertion point and oriented visible bounds in world space."""
        frame = np.asarray(self._frame, dtype=float)
        corners = self._local_box()
        mids = (corners + np.roll(corners, -1, axis=0)) / 2.
        center = corners.mean(axis=0)

        def mapped(points, kind):
            return [(tuple((frame @ point)[:3]), kind) for point in points]

        return ([(self.origin, "point")]
                + mapped(corners, "end")
                + mapped(mids, "mid")
                + mapped([center], "center"))

    def to_curves(self):
        """Independent ordinary wires, retaining separate letter counters."""
        wires = []
        explorer = occ.TopExp_Explorer(self._brep, occ.WIRE)
        while explorer.More():
            wires.append(geometry.copy_shape(explorer.Current()))
            explorer.Next()
        return wires

    def fill(self):
        """The glyphs as planar faces, counters left open: what is drawn of
        the text, like a solid hatch. None when the outlines do not close
        into regions."""
        if not hasattr(self, "_fill"):
            try:
                faces = geometry.planar_regions(self.to_curves())
                self._fill = geometry.make_compound(faces) if faces else None
            except Exception:                              # noqa: BLE001
                self._fill = None
        return self._fill

    def to_bytes(self):
        header = json.dumps(dict(typography=self._typography(), frame=self._frame,
                                 look=self._look()),
                            ensure_ascii=False).encode("utf-8")
        return (TEXT_TAG + struct.pack("<I", len(header)) + header
                + geometry.shape_to_bytes(self._brep))

    @classmethod
    def from_bytes(cls, data):
        start = len(TEXT_TAG)
        size, = struct.unpack("<I", data[start:start + 4])
        start += 4
        header = json.loads(data[start:start + size])
        brep = geometry.shape_from_bytes(data[start + size:])
        return cls._from_geometry(header["typography"], header["frame"], brep,
                                  header.get("look"))


class TextPreview(TopoDS_Compound):
    """A preview of several shapes that remembers which were text, so a
    ghost can draw their dotted frames as their selection shows them."""

    def __init__(self, compound, texts):
        super().__init__()
        self.TShape(compound.TShape())
        self.Location(compound.Location())
        self.Orientation(compound.Orientation())
        self.texts = list(texts)


_UNKNOWN = object()


def _joined(parts):
    """Glyph meshes set at their offsets as one: (points, facing,
    triangles, regions, (low, high) or (None, None))."""
    points, facing, triangles, regions = [], [], [], []
    los, his = [], []
    start = region = 0
    for (pts, face, tris, owner, box), x, y in parts:
        shift = np.array([x, y])
        if len(pts):
            points.append(pts + shift)
            facing.append(face)
            triangles.append(tris + start)
            regions.append(owner + region)
            start += len(pts)
            region += int(owner.max()) + 1 if len(owner) else 0
        if box is not None:
            los.append(box[0] + shift)
            his.append(box[1] + shift)
    if not points:
        return (np.zeros((0, 2)), np.zeros(0), np.zeros((0, 3), np.uint32),
                np.zeros(0, np.int32),
                (np.min(los, axis=0), np.max(his, axis=0)) if los
                else (None, None))
    return (np.concatenate(points), np.concatenate(facing),
            np.concatenate(triangles).astype(np.uint32),
            np.concatenate(regions).astype(np.int32),
            (np.min(los, axis=0), np.max(his, axis=0)) if los
            else (None, None))


def _carried(shape, matrix):
    """`shape` put through `matrix`: a move or turn only relocates it, which
    keeps the triangulation it already has; anything else rebuilds it."""
    a = matrix[:3, :3]
    if not (np.allclose(a @ a.T, np.eye(3), atol=1e-9)
            and np.linalg.det(a) > 0):
        return geometry.apply_matrix(shape, matrix)
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf
    trsf = gp_Trsf()
    trsf.SetValues(*matrix[0], *matrix[1], *matrix[2])
    return shape.Moved(TopLoc_Location(trsf))


def dotted_frame(corners, screen, spacing: float, dot: float) -> np.ndarray:
    """The dots of a dotted frame through `corners`, a closed ring of
    points in 2D or 3D, as (K, 2, D) short segments: one on every corner,
    the rest spread evenly between. `screen` is the same ring where it is
    seen, in pixels, and `spacing` and `dot` are measured there, so an
    edge seen end on gets few dots however long it really is.
    What marks picked text, which as a fill has no outline of its own."""
    corners = np.asarray(corners, float)
    screen = np.asarray(screen, float)
    out = []
    for i, (a, b) in enumerate(zip(corners, np.roll(corners, -1, axis=0))):
        seen = float(np.linalg.norm(screen[(i + 1) % len(screen)]
                                    - screen[i]))
        if seen < 1e-9:
            continue
        count = min(max(1, round(seen / spacing)), 128)
        starts = a + np.outer(np.arange(count) / count, b - a)
        out.append(np.stack([starts, starts + (b - a) * min(dot / seen, 1.)],
                            1))
    if not out:
        return np.zeros((0, 2, corners.shape[1]))
    return np.concatenate(out)


def output_shapes(text: TextShape, output: str, depth: float = 1.) -> list:
    """Turn editable lettering into ordinary geometry on its stored plane."""
    if output == "editable":
        return [text]
    if output not in ("curves", "surface", "solid"):
        raise geometry.GeometryError(f"Unknown text output: {output}")
    curves = text.to_curves()
    if output == "curves":
        return curves
    if output == "surface":
        return geometry.planar_regions(curves)
    if output == "solid":
        if not math.isfinite(depth) or depth <= 0:
            raise geometry.GeometryError("Text solid depth must be positive")
        return geometry.extrude_profiles(
            curves, text.plane_normal, float(depth), cap=True)
