"""The graph's preview in the model viewports, meshed once per shape."""

from __future__ import annotations

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopoDS import TopoDS, TopoDS_Shape


MESH_WIRES_UP_TO = 50000    # triangles a mesh may have to show all its edges


class PreviewMeshes:
    """The preview's triangles, segments, points, glyphs and backdrops, as
    the viewport's overlay draw takes them. Glyphs are text, filled from the
    font's own letters as the model draws editable text, and backdrops the
    patches under text that has a background.

    Meshing is what a preview costs, so each shape is meshed once, without
    its placement, and only turned into place on every solve after. A
    rotated shape keeps its surfaces and changes only its placement, which
    is what makes dragging a slider into a Rotate run smoothly.
    """

    def __init__(self):
        self._kept: dict = {}
        # the very objects shown last time, already in place
        self._placed: dict = {}

    def overlay(self, shapes):
        return self.overlays([shapes])[0]

    def overlays(self, groups):
        """An overlay for each group of shapes, meshed with one cache."""
        kept, placed, out = {}, {}, []
        for shapes in groups:
            parts = ([], [], [], [], [])
            for shape in shapes:
                done = placed.get(id(shape)) or self._placed.get(id(shape))
                if done is None or done[0] is not shape:
                    done = self._place(shape, kept)
                if done[1] is not None:
                    kept[done[1]] = done[2]
                placed[id(shape)] = done
                for part, arr in zip(parts, done[3]):
                    if len(arr):
                        part.append(arr)
            out.append(tuple(np.concatenate(part) if part
                             else np.empty((0, 3), np.float32)
                             for part in parts))
        self._kept, self._placed = kept, placed
        return out

    def _place(self, shape, kept):
        """(shape, key, meshed, in place): a point needs no meshing."""
        point = _vertex_point(shape)
        if point is not None:
            return shape, None, None, (_EMPTY, _EMPTY, point, _EMPTY, _EMPTY)
        base, matrix = _unplaced(shape)
        key = hash(base) if matrix is not None else ("obj", id(shape))
        entry = self._kept.get(key) or kept.get(key)
        if entry is None or not _same(entry[0], base):
            entry = (base, _mesh_arrays(base))
        return shape, key, entry, tuple(
            arr if matrix is None
            else arr @ matrix[:3, :3].T + matrix[:3, 3]
            for arr in entry[1])


_EMPTY = np.empty((0, 3))


def _vertex_point(shape):
    """A point shape's place, as one row; None for any other shape."""
    if (isinstance(shape, TopoDS_Shape)
            and shape.ShapeType() == TopAbs_ShapeEnum.TopAbs_VERTEX):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(shape))
        return np.array([[p.X(), p.Y(), p.Z()]])
    return None


def _unplaced(shape):
    """An OCC shape without its placement, and the placement as a matrix;
    anything else as it is, with no matrix."""
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS_Shape
    from ...core.text_object import TextShape
    # unplaced, text would be bare outlines and lose its glyphs
    if not isinstance(shape, TopoDS_Shape) or isinstance(shape, TextShape):
        return shape, None
    trsf = shape.Location().Transformation()
    matrix = np.array([[trsf.Value(r, c) for c in range(1, 5)]
                       for r in range(1, 4)] + [[0.0, 0.0, 0.0, 1.0]])
    return shape.Located(TopLoc_Location()), matrix


def _same(a, b):
    from OCP.TopoDS import TopoDS_Shape
    return a.IsEqual(b) if isinstance(a, TopoDS_Shape) else a is b


def _mesh_arrays(shape):
    from ...core.tessellate import tessellate
    from ...core.text_object import TextShape
    empty = np.empty((0, 3))
    wires = _mesh_wires(shape)
    if wires is not None:
        # a mesh Wyrm made, drawn as it is: its own triangles and every
        # edge, nothing worked out that would be thrown away
        tris = shape.vertices[shape.triangles.ravel()].astype(float)
        return tris, wires, empty, empty, empty
    try:
        mesh = tessellate(shape)
    except Exception:                                      # noqa: BLE001
        return empty, empty, empty, empty, empty
    tris = (mesh.vertices[mesh.triangles.ravel()].astype(float)
            if len(mesh.triangles) else empty)
    if isinstance(shape, TextShape):
        # filled letters and no outline, as text is in the model
        backdrop = (np.asarray(shape.frame_box(), float)[[0, 1, 2, 0, 2, 3]]
                    if shape.background else empty)
        return empty, empty, empty, tris, backdrop
    segs = (mesh.edge_segments.reshape(-1, 3).astype(float)
            if len(mesh.edge_segments) else empty)
    wires = _mesh_wires(shape)
    if wires is not None:
        segs = wires
    points = mesh.points.astype(float) if len(mesh.points) else empty
    return tris, segs, points, empty, empty


def _mesh_wires(shape):
    """Every edge of a mesh's triangles, for a mesh small enough to show
    them all: the model shows a mesh's rim and creases only, which hides how
    a mesh Wyrm made, a Delaunay one say, is triangulated. None for other
    shapes, and for a mesh as big as a scan."""
    from ...core.mesh import MeshShape
    if not isinstance(shape, MeshShape) or not (
            0 < len(shape.triangles) <= MESH_WIRES_UP_TO):
        return None
    tris = shape.triangles.astype(np.int64)
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]],
                            tris[:, [2, 0]]])
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    return shape.vertices[edges].reshape(-1, 3).astype(float)
