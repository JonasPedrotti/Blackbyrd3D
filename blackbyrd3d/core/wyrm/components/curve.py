"""Contour, and Point On Curve."""

from __future__ import annotations

import numpy as np

from ... import geometry as g
from ...mesh import MeshShape
from . import COMPONENTS, Component
from ..kinds import GeometryGroup, WyrmError, Port, Vector

MOST_CONTOURS = 2000        # the most levels one shape is cut at
KEEP_CUTS_OF = 4            # meshes whose cuts are kept, the latest ones

# A mesh's cuts by level, so a slider that only changes which levels are
# drawn hands on the same curves again: (mesh, {(direction, level): curves})
_CUTS: dict[int, tuple] = {}


def _contour(G, D, N, S=0.0):
    if D <= 0:
        raise WyrmError("Distance must be more than 0")
    direction = np.asarray(N.components, float)
    if np.linalg.norm(direction) < 1e-12:
        raise WyrmError("Direction has no length")
    direction /= np.linalg.norm(direction)
    if isinstance(G, GeometryGroup):
        raise WyrmError("Contour cuts one shape at a time: ungroup it first")
    kind = g.shape_kind(G)
    if kind not in ("surface", "solid", "mesh"):
        raise WyrmError("Contour cuts surfaces, solids and meshes, not "
                         f"{kind}s")
    low, high = G.bbox() if isinstance(G, MeshShape) else g.bbox(G)
    corners = np.array([[x, y, z] for x in (low[0], high[0])
                        for y in (low[1], high[1])
                        for z in (low[2], high[2])])
    along = corners @ direction
    if (along.max() - along.min()) / D > MOST_CONTOURS:
        raise WyrmError(f"That makes more than {MOST_CONTOURS:,} contours: "
                         "take a larger distance")
    # at whole steps from the origin, as a map's contours are at round
    # heights, not from wherever the geometry happens to start
    first = np.floor(along.min() / D) * D
    levels = [level for level in np.arange(first, along.max() + D, D)
              if along.min() + 1e-6 < level < along.max() - 1e-6
              and not _skipped(level, S)]
    curves = []
    for level in levels:
        if isinstance(G, MeshShape):
            curves.extend(_mesh_cut(G, direction, level))
            continue
        try:
            curves.extend(g.section_curves(G, tuple(direction * level),
                                           tuple(direction)))
        except g.GeometryError:
            pass             # one sour level must not lose the others
    if not curves:
        raise WyrmError("The distance is larger than the geometry: no "
                         "contour fits in it")
    return curves


def _skipped(level, every):
    """Whether a level is one Skip every leaves out: a whole multiple of
    it, as the major contours another Contour draws; none for 0."""
    if every <= 0:
        return False
    times = level / every
    return abs(times - round(times)) < 1e-6


def _mesh_cut(mesh, direction, level):
    """A triangle mesh cut by the plane `level` along `direction`, as
    polylines, closed where they meet themselves again."""
    kept = _CUTS.get(id(mesh))
    if kept is None or kept[0] is not mesh:
        kept = (mesh, {})
        _CUTS[id(mesh)] = kept
        while len(_CUTS) > KEEP_CUTS_OF:
            del _CUTS[next(iter(_CUTS))]
    key = (tuple(np.round(direction, 12)), round(float(level), 9))
    if key not in kept[1]:
        kept[1][key] = _cut_mesh(mesh, direction, level)
    return list(kept[1][key])


def _cut_mesh(mesh, direction, level):
    side = mesh.vertices @ direction - level
    # a corner lying on the plane counts as just above it, so every
    # triangle the plane cuts has exactly two edges crossing it
    side[np.abs(side) < 1e-12] = 1e-12
    return _cut(mesh.vertices, mesh.triangles.astype(np.int64), side)


def _cut(vertices, triangles, side):
    above = side[triangles] > 0
    cut = triangles[above.any(axis=1) & ~above.all(axis=1)]
    if not len(cut):
        return []
    # each cut triangle gives one piece, between the two edges the plane
    # crosses; an edge is named by its two corners, so neighbours share it
    n = len(vertices)
    lo = np.minimum(cut, np.roll(cut, -1, axis=1))
    hi = np.maximum(cut, np.roll(cut, -1, axis=1))
    crossing = (side[lo] > 0) != (side[hi] > 0)
    names = (lo * n + hi)[crossing].reshape(-1, 2)
    edges, piece_ends = np.unique(names, return_inverse=True)
    piece_ends = piece_ends.reshape(-1, 2)
    i, j = edges // n, edges % n
    t = (side[i] / (side[i] - side[j]))[:, None]
    where = (vertices[i] + t * (vertices[j] - vertices[i])).tolist()
    at = [[] for _ in range(len(edges))]
    for k, (e, f) in enumerate(piece_ends.tolist()):
        at[e].append(k)
        at[f].append(k)
    ends = piece_ends.tolist()
    used = [False] * len(ends)
    curves = []
    # chains that end at the mesh's border first, so they are walked from
    # one end; the rest are rings
    order = sorted(range(len(ends)), key=lambda k: min(
        len(at[ends[k][0]]), len(at[ends[k][1]])))
    for first in order:
        if used[first]:
            continue
        used[first] = True
        e, f = ends[first]
        if len(at[f]) == 1:
            e, f = f, e                   # start from the border end
        chain = [e, f]
        while True:
            nxt = [k for k in at[chain[-1]] if not used[k]]
            if not nxt:
                break
            used[nxt[0]] = True
            a, b = ends[nxt[0]]
            chain.append(b if a == chain[-1] else a)
        points = [where[chain[0]]]
        for e in chain[1:]:
            p = where[e]
            q = points[-1]
            if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) > 1e-9:
                points.append(p)
        if len(points) >= 2:
            # one curve of degree 1, as Rhino keeps a polyline: much quicker
            # to make and to draw than an edge for every piece
            curves.append(g.make_control_curve(points, degree=1))
    return curves


COMPONENTS["contour"] = Component(
    "contour", "Contour", "Curve",
    inputs=(Port("G", "geometry", label="Geometry",
                 description="The surfaces, solids or meshes to cut"),
            Port("D", "number", 1.0, label="Distance",
                 description="How far apart the contours are"),
            Port("N", "vector", Vector((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
                 label="Direction",
                 description="Which way the contours are spaced: square to "
                             "their planes, upwards (Z) unless set"),
            Port("S", "number", 0.0, label="Skip every",
                 description="Leaves out the heights that are a multiple of "
                             "it, such as every 5th, drawn by another "
                             "Contour; none unless set")),
    outputs=(Port("C", "curve", access="list", label="Curves",
                  description="The contour curves"),),
    icon="contour", solve=_contour,
    description="Cuts G, a Brep or a mesh, with planes D apart along N, as "
                "contour lines on a map: at whole steps of D from the "
                "origin, upwards (Z) by default")


def _point_on_curve(C, t):
    from OCP.BRepAdaptor import BRepAdaptor_CompCurve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.gp import gp_Pnt, gp_Vec
    from ... import occ
    if not 0 <= t <= 1:
        raise WyrmError("t runs from 0, the start, to 1, the end")
    kind = C.ShapeType()
    if kind == occ.WIRE:
        adaptor = BRepAdaptor_CompCurve(occ.to_wire(C))
    elif kind == occ.EDGE:
        adaptor = occ.edge_adaptor(occ.to_edge(C))
    else:
        raise WyrmError("Point On Curve takes one curve at a time")
    # t is a share of the length, not of the curve's own parameter, so 0.5
    # is the middle however the curve was drawn
    length = GCPnts_AbscissaPoint.Length_s(adaptor)
    at = GCPnts_AbscissaPoint(adaptor, t * length,
                              adaptor.FirstParameter()).Parameter()
    point, tangent = gp_Pnt(), gp_Vec()
    adaptor.D1(at, point, tangent)
    where = (point.X(), point.Y(), point.Z())
    if tangent.Magnitude() < 1e-12:
        raise WyrmError("The curve has no direction there")
    tangent.Normalize()
    return (g.make_point(where),
            Vector(where, (where[0] + tangent.X(), where[1] + tangent.Y(),
                           where[2] + tangent.Z())))


COMPONENTS["point_on_curve"] = Component(
    "point_on_curve", "Point On Curve", "Curve",
    inputs=(Port("C", "curve", label="Curve",
                 description="The curve to find the point on"),
            Port("t", "number", 0.5, label="Where",
                 description="How far along: 0 the start, 1 the end, the "
                             "middle unless set")),
    outputs=(Port("P", "point", label="Point",
                  description="The point that far along"),
             Port("D", "vector", label="Direction",
                  description="Which way the curve runs there")),
    icon="pointoncurve", solve=_point_on_curve,
    description="The point t of the way along C, and the way the curve runs "
                "there: the middle unless set")
