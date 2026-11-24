"""Coplanar neighbours fused for shapes of flat faces and straight edges.

ShapeUpgrade_UnifySameDomain took a minute and a half on a mesh turned
into a Brep, a hundred thousand triangles, because it asks every pair of
neighbours what their surfaces are as if they could be anything. When every
face is a plane and every edge a line, which faces belong together is a
question about normals and shared edges that numpy answers at once, and
the new faces are only their groups' outer boundaries put back together.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import occ
from .occ import BRep_Builder, BRep_Tool, TopExp, TopExp_Explorer, TopoDS

# Faces are one plane, and edges one line, when their corners are no
# further off it than the drawing's tolerance, or their own when larger.
# Faces whose normals are this close, in degrees, are one plane as well:
# a wall exported a hair askew is flat to the eye however long it is,
# while the facets of a column turn further than this from one to the next.
ANGLE = 0.5


@dataclass
class Merged:
    shape: object
    # old face number -> new face number, and old edge number -> new edge
    # number, -1 for one that went, both in TopExp_Explorer order, which is
    # how a display mesh counts them
    face_map: np.ndarray
    edge_map: np.ndarray
    faces_before: int
    faces_after: int


class _Unmergeable(Exception):
    pass


def merge_flat(shape, progress=None, tolerance: float | None = None,
               angle: float = ANGLE) -> Merged | None:
    """Fuse coplanar neighbours of a shape made only of planes and lines,
    or None for any other shape, which UnifySameDomain then has to do.
    `tolerance` is the drawing's own unless given, `angle` in degrees."""
    from ..fileio.progress import Progress
    from .tolerance import tol
    progress = progress or Progress()
    linear = tol() if tolerance is None else tolerance
    square = float(np.cos(np.radians(angle)))
    try:
        return _merge(shape, progress, linear, square)
    except _Unmergeable:
        return None


def _merge(shape, progress, linear, square):
    from OCP.Geom import Geom_Plane
    from OCP.GeomAbs import GeomAbs_CurveType
    from OCP.TopAbs import TopAbs_Orientation

    if not isinstance(shape, occ.TopoDS_Shape) or shape.IsNull() \
            or not shape.Location().IsIdentity():
        raise _Unmergeable
    forward = TopAbs_Orientation.TopAbs_FORWARD
    backward = TopAbs_Orientation.TopAbs_REVERSED
    fmap = occ.map_shapes(shape, occ.FACE)
    emap = occ.map_shapes(shape, occ.EDGE)
    vmap = occ.map_shapes(shape, occ.VERTEX)
    nf, ne, nv = fmap.Extent(), emap.Extent(), vmap.Extent()
    if nf < 2:
        raise _Unmergeable

    line = GeomAbs_CurveType.GeomAbs_Line
    first, last = TopExp.FirstVertex_s, TopExp.LastVertex_s
    ends = np.empty((ne, 2), np.int64)
    eslack = np.empty(ne)
    for i in range(ne):
        if not i % 4000:
            progress(0.3 * i / ne, "Reading edges")
        edge = TopoDS.Edge_s(emap.FindKey(i + 1))
        if BRep_Tool.Degenerated_s(edge) \
                or occ.edge_adaptor(edge).GetType() != line:
            raise _Unmergeable
        ends[i] = (vmap.FindIndex(first(edge)) - 1,
                   vmap.FindIndex(last(edge)) - 1)
        eslack[i] = BRep_Tool.Tolerance_s(edge)
    where = np.empty((nv, 3))
    vslack = np.empty(nv)
    for i in range(nv):
        vertex = TopoDS.Vertex_s(vmap.FindKey(i + 1))
        where[i] = BRep_Tool.Pnt_s(vertex).Coord()
        vslack[i] = BRep_Tool.Tolerance_s(vertex)
    held = vslack.copy()
    vslack = np.maximum(vslack, linear)

    slack, faces, he_face, he_edge, he_back = [], [], [], [], []
    exp = TopExp_Explorer(shape, occ.FACE)
    k = 0
    while exp.More():
        if not k % 4000:
            progress(0.3 + 0.3 * k / nf, "Reading faces")
        face = TopoDS.Face_s(exp.Current())
        exp.Next()
        side = face.Orientation()
        if side != forward and side != backward \
                or not isinstance(BRep_Tool.Surface_s(face), Geom_Plane):
            raise _Unmergeable
        slack.append(BRep_Tool.Tolerance_s(face))
        faces.append(face)
        edges = TopExp_Explorer(face, occ.EDGE)
        while edges.More():
            edge = edges.Current()
            edges.Next()
            o = edge.Orientation()
            if o != forward and o != backward:
                raise _Unmergeable
            he_face.append(k)
            he_edge.append(emap.FindIndex(edge) - 1)
            he_back.append(o == backward)
        k += 1
    if k != nf:
        raise _Unmergeable                # a face met twice
    slack = np.maximum(np.asarray(slack, float), linear)
    hf = np.asarray(he_face, np.int64)
    he = np.asarray(he_edge, np.int64)
    hb = np.asarray(he_back, bool)
    # each half-edge runs from its start to its end as the face walks it
    start = np.where(hb, ends[he, 1], ends[he, 0])
    stop = np.where(hb, ends[he, 0], ends[he, 1])
    corners = where[start]
    # a face's half-edges are listed together, so its corners are a run
    runs = np.searchsorted(hf, np.arange(nf + 1))
    if (np.diff(runs) < 3).any():
        raise _Unmergeable
    # Newell's normal, the way the face walks round, so the side it looks
    # out of and twice its area
    origins = corners[runs[:-1]]
    newell = np.add.reduceat(np.cross(corners - origins[hf],
                                      where[stop] - origins[hf]),
                             runs[:-1])
    area = np.linalg.norm(newell, axis=1)
    if not (area > 0).all():
        raise _Unmergeable
    normals = newell / area[:, None]

    progress(0.62, "Finding coplanar faces")
    doubled = _doubled(start, runs, normals)
    kept = np.nonzero(~doubled[hf])[0]
    counts = np.bincount(he[kept], minlength=ne)
    order = kept[np.argsort(he[kept], kind="stable")]
    firsts = np.searchsorted(he[order], np.arange(ne))
    pair = np.nonzero(counts == 2)[0]
    ha, hb2 = order[firsts[pair]], order[firsts[pair] + 1]
    fa, fb = hf[ha], hf[hb2]
    if np.any(fa == fb):
        raise _Unmergeable                # a seam inside one face
    allowed = np.maximum(slack[fa], slack[fb])
    facing = np.einsum("ij,ij->i", normals[fa], normals[fb])
    close = ((_off_plane(fa, fb, normals, origins, corners, runs) <= allowed)
             & (_off_plane(fb, fa, normals, origins, corners, runs)
                <= allowed))
    same = (facing > 0) & (hb[ha] != hb[hb2]) & (close | (facing >= square))
    progress(0.64, "Finding coplanar faces")
    label = _grow(nf, fa[same], fb[same], area, normals, origins, corners,
                  runs, slack, square)

    sizes = np.bincount(label, minlength=nf)
    owner = label[hf]
    # each group's plane: its faces' normals weighted by their areas,
    # through the middle of their corners
    plane_n = np.zeros((nf, 3))
    np.add.at(plane_n, label, newell)
    plane_n /= np.maximum(np.linalg.norm(plane_n, axis=1), 1e-300)[:, None]
    plane_o = np.zeros((nf, 3))
    np.add.at(plane_o, owner, corners)
    plane_o /= np.maximum(np.bincount(owner, minlength=nf), 1)[:, None]
    ours = np.nonzero(sizes[owner] > 1)[0]
    lead = owner[ours]
    drift = np.zeros(nf)
    np.maximum.at(drift, lead, np.abs(np.einsum(
        "ij,ij->i", plane_n[lead], corners[ours] - plane_o[lead])))
    inside = (label[fa] == label[fb]) & (sizes[label[fa]] > 1)
    interior = np.zeros(ne, bool)
    interior[pair[inside]] = True

    progress(0.68, "Tracing the merged faces")
    rows = np.nonzero((sizes[owner] > 1) & ~interior[he])[0]
    loops, dropped = {}, []
    # beside faces that went, a face can be left folding back on itself
    beside = set(np.unique(owner[kept][np.isin(he[kept],
                                               he[doubled[hf]])]).tolist())
    traced = _split(rows, owner[rows])
    for i, (g, own) in enumerate(traced.items()):
        if not i % 500:
            progress(0.66 + 0.12 * i / len(traced), "Tracing the merged faces")
        found = _loops(own, he, hb, start, stop, plane_n[g], where)
        if found is not None and g in beside \
                and not _simple(found, plane_n[g], where, linear):
            found = None
        if found is None:
            dropped.append(g)
        else:
            loops[g] = found
    if dropped:
        # pinched or folded: those faces stay as they are
        out = np.isin(label, dropped)
        interior[pair[inside & out[fa]]] = False
        label[out] = np.nonzero(out)[0]
        owner = label[hf]

    chains, chain_of, gone = _edge_chains(ne, nv, ends, where, vslack,
                                          interior, he[kept], hf[kept],
                                          label)
    if chains:
        touched = np.unique(owner[kept][chain_of[he[kept]] >= 0])
        for g in touched.tolist():
            if g in loops:
                continue
            own = np.nonzero((owner == g) & ~interior[he])[0]
            found = _loops(own, he, hb, start, stop, normals[g], where)
            if found is None:
                raise _Unmergeable
            loops[g] = found
    if not loops and not doubled.any():
        return Merged(shape, np.arange(nf), np.arange(ne), nf, nf)
    members_of = _split(np.arange(nf), label)

    progress.tick(0.8, "Building the merged faces")
    builder = BRep_Builder()
    made_edges = []
    for a, b in chains:
        made_edges.append(occ.BRepBuilderAPI_MakeEdge(
            TopoDS.Vertex_s(vmap.FindKey(a + 1)),
            TopoDS.Vertex_s(vmap.FindKey(b + 1))).Edge())
    from OCP.BRepTools import BRepTools_ReShape
    from OCP.Geom import Geom_Plane as Plane
    reshape = BRepTools_ReShape()
    made_faces = {}
    for g, found in loops.items():
        members = members_of[g]
        lead = int(members[0])
        face = occ.TopoDS_Face()
        n, o = (plane_n[g], plane_o[g]) if len(members) > 1 \
            else (normals[lead], origins[lead])
        builder.MakeFace(face, Plane(occ.gp_Pnt(*o), occ.gp_Dir(*n)),
                         max(BRep_Tool.Tolerance_s(faces[lead]),
                             float(drift[g])))
        for loop in found:
            wire = occ.TopoDS_Wire()
            builder.MakeWire(wire)
            for e, back, s in loop:
                c = chain_of[e]
                if c >= 0:
                    if gone[s]:
                        continue
                    edge = made_edges[c]
                    back = s != chains[c][0]
                    tips = chains[c]
                    own = BRep_Tool.Tolerance_s(edge)
                else:
                    edge = TopoDS.Edge_s(emap.FindKey(e + 1))
                    tips = ends[e]
                    own = eslack[e]
                # the plane is fitted to every face it replaces, so an
                # edge can sit a hair off it: the edge is told how far
                gap = np.abs((where[list(tips)] - o) @ n)
                if gap.max() > own:
                    builder.UpdateEdge(edge, float(gap.max()) * 1.01)
                    if c < 0:
                        eslack[e] = gap.max() * 1.01
                for t, d in zip(tips, gap.tolist()):
                    if d > held[t]:
                        held[t] = d * 1.01
                        builder.UpdateVertex(
                            TopoDS.Vertex_s(vmap.FindKey(int(t) + 1)),
                            held[t])
                builder.Add(wire, edge.Oriented(backward if back
                                                else forward))
            wire.Closed(True)
            builder.Add(face, wire)
        made_faces[g] = face
        reshape.Replace(faces[lead], face)
        for m in members[1:].tolist():
            reshape.Remove(faces[m])
    for f in np.nonzero(doubled)[0].tolist():
        reshape.Remove(faces[f])
    progress.tick(0.9, "Putting the shape back together")
    result = reshape.Apply(shape)
    _keep_closed(shape, result)

    face_map = np.full(nf, -1, np.int64)
    made_map = occ.TopTools_IndexedMapOfShape()
    groups_made = list(made_faces)
    for g in groups_made:
        made_map.Add(made_faces[g])
    exp = TopExp_Explorer(result, occ.FACE)
    j = 0
    while exp.More():
        f = exp.Current()
        exp.Next()
        old = fmap.FindIndex(f)
        if old:
            face_map[old - 1] = j
        else:
            at = made_map.FindIndex(f)
            if not at:
                raise _Unmergeable
            face_map[members_of[groups_made[at - 1]]] = j
        j += 1
    if (face_map[~doubled] < 0).any():
        raise _Unmergeable

    new_edges = occ.map_shapes(result, occ.EDGE)
    chain_map = occ.TopTools_IndexedMapOfShape()
    for edge in made_edges:
        chain_map.Add(edge)
    edge_map = np.full(ne, -1, np.int64)
    chained = np.nonzero(chain_of >= 0)[0]
    runs_of = _split(chained, chain_of[chained])
    for i in range(new_edges.Extent()):
        edge = new_edges.FindKey(i + 1)
        old = emap.FindIndex(edge)
        if old:
            edge_map[old - 1] = i
        else:
            c = chain_map.FindIndex(edge)
            if not c:
                raise _Unmergeable
            edge_map[runs_of[c - 1]] = i
    # twice each face's area, holes wound the other way and taken off
    from . import geometry
    geometry.know_area(result, 0.5 * float(area[~doubled].sum()))
    return Merged(result, face_map, edge_map, nf, j)


def _doubled(start, runs, normals) -> np.ndarray:
    """Faces lying on another face corner for corner. Back to back they are
    where two bodies stacked on each other touch, inside the whole, and
    both go; facing the same way one is a copy, and one of them stays."""
    out = np.zeros(len(runs) - 1, bool)
    alike = {}
    corners, rl = start.tolist(), runs.tolist()
    for f in range(len(rl) - 1):
        alike.setdefault(tuple(sorted(corners[rl[f]:rl[f + 1]])), []) \
            .append(f)
    for faces in alike.values():
        if len(faces) < 2:
            continue
        ref = normals[faces[0]]
        up = [f for f in faces if normals[f] @ ref > 0]
        down = [f for f in faces if normals[f] @ ref <= 0]
        left = up[len(down):] or down[len(up):]
        out[faces] = True
        if left:
            out[left[0]] = False
    return out


def _grow(n, a, b, area, normals, origins, corners, runs, slack, square):
    """Faces grouped from the largest down: each group takes in the
    neighbours joined to it by (a, b) whose corners all lie on its first
    face's plane, or which face the same way within the angle, so a gentle
    curve in small steps never adds up to a flat face. Each face is
    labelled with its group's first face."""
    near = np.concatenate([a, b])
    far = np.concatenate([b, a])
    by = np.argsort(near, kind="stable")
    near, far = near[by], far[by]
    ptr = np.searchsorted(near, np.arange(n + 1)).tolist()
    far = far.tolist()
    label = [-1] * n
    nl, ol, cl = normals.tolist(), origins.tolist(), corners.tolist()
    rl, sl = runs.tolist(), slack.tolist()
    for seed in np.argsort(-area, kind="stable").tolist():
        if label[seed] >= 0:
            continue
        label[seed] = seed
        if ptr[seed] == ptr[seed + 1]:
            continue
        nx, ny, nz = nl[seed]
        ox, oy, oz = ol[seed]
        reach = sl[seed]
        stack = [seed]
        while stack:
            f = stack.pop()
            for g in far[ptr[f]:ptr[f + 1]]:
                if label[g] >= 0:
                    continue
                m = nl[g]
                facing = nx * m[0] + ny * m[1] + nz * m[2]
                if facing <= 0:
                    continue
                if facing >= square:
                    label[g] = seed
                    stack.append(g)
                    continue
                lim = max(reach, sl[g])
                for x, y, z in cl[rl[g]:rl[g + 1]]:
                    if abs(nx * (x - ox) + ny * (y - oy)
                           + nz * (z - oz)) > lim:
                        break
                else:
                    label[g] = seed
                    stack.append(g)
    return _join_groups(np.asarray(label, np.int64), a, b, area, normals,
                        origins, corners, runs, slack, square)


def _join_groups(label, a, b, area, normals, origins, corners, runs, slack,
                 square):
    """Neighbouring groups made one where the smaller lies on the larger's
    plane: growing from the largest face first can leave a flat stretch
    split between two seeds that each reached it from their own side."""
    owner = np.repeat(np.arange(len(runs) - 1), np.diff(runs))
    while True:
        touching = label[a] != label[b]
        if not touching.any():
            return label
        g1, g2 = label[a[touching]], label[b[touching]]
        links = np.unique(np.stack([np.minimum(g1, g2),
                                    np.maximum(g1, g2)], axis=1), axis=0)
        weight = np.bincount(label, weights=area, minlength=len(label))
        rows = _split(np.arange(len(owner)), label[owner])
        reach = np.zeros(len(label))
        np.maximum.at(reach, label, slack)
        into = np.arange(len(label))

        def home(x):
            while into[x] != x:
                into[x] = into[into[x]]
                x = into[x]
            return x

        changed = False
        for x, y in links.tolist():
            x, y = home(x), home(y)
            if x == y:
                continue
            big, small = (x, y) if weight[x] >= weight[y] else (y, x)
            lim = max(reach[big], reach[small])
            for keep, give in ((big, small), (small, big)):
                pts = corners[rows[give]]
                turn = (normals[owner[rows[give]]] @ normals[keep]).min()
                off = np.abs((pts - origins[keep]) @ normals[keep]).max()
                if turn >= square or off <= lim and turn > 0:
                    rows[keep] = np.concatenate([rows[keep], rows[give]])
                    del rows[give]
                    weight[keep] += weight[give]
                    reach[keep] = lim
                    into[give] = keep
                    changed = True
                    break
        if not changed:
            return label
        label = np.fromiter((home(x) for x in label.tolist()), np.int64,
                            len(label))


def _components(n, a, b) -> np.ndarray:
    """Each of n items labelled with the smallest item it is joined to."""
    parent = list(range(n))

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for x, y in zip(a.tolist(), b.tolist()):
        rx, ry = root(x), root(y)
        if rx != ry:
            if rx < ry:
                parent[ry] = rx
            else:
                parent[rx] = ry
    return np.fromiter((root(x) for x in range(n)), np.int64, n)


def _off_plane(planes, faces, normals, origins, corners, runs):
    """How far each of `faces` strays from the plane of the face beside
    it in `planes`, at its furthest corner."""
    first, count = runs[faces], runs[faces + 1] - runs[faces]
    begin = np.cumsum(count) - count
    rows = np.arange(count.sum()) - np.repeat(begin - first, count)
    plane = np.repeat(planes, count)
    gap = np.abs(np.einsum("ij,ij->i", normals[plane],
                           corners[rows] - origins[plane]))
    return np.maximum.reduceat(gap, begin)


def _split(rows, keys) -> dict:
    """{key: its rows}, rows in the order they came."""
    if not len(rows):
        return {}
    order = np.argsort(keys, kind="stable")
    rows, keys = rows[order], keys[order]
    cuts = np.nonzero(np.diff(keys))[0] + 1
    return {int(k[0]): r for k, r in zip(np.split(keys, cuts),
                                         np.split(rows, cuts))}


def _loops(rows, he, hb, start, stop, normal, where):
    """The closed loops the half-edges `rows` make, outer one first, each a
    list of (edge, walked backwards, start vertex); None when they do not
    close up into one outer loop and its holes."""
    after = {}
    for r, s in zip(rows.tolist(), start[rows].tolist()):
        if s in after:
            return None                   # two ways on from one corner
        after[s] = r
    loops, areas = [], []
    left = set(rows.tolist())
    while left:
        r = left.pop()
        loop = [r]
        s0 = int(start[r])
        at = int(stop[r])
        while at != s0:
            r = after.get(at)
            if r is None or r not in left:
                return None
            left.discard(r)
            loop.append(r)
            at = int(stop[r])
        if len(loop) < 3:
            return None
        corners = where[start[loop]]
        newell = np.cross(corners, np.roll(corners, -1, axis=0)).sum(axis=0)
        loops.append(loop)
        areas.append(float(np.dot(newell, normal)))
    outer = [i for i, a in enumerate(areas) if a > 0]
    if len(outer) != 1:
        return None
    first = outer[0]
    ordered = [loops[first]] + [lp for i, lp in enumerate(loops)
                                if i != first]
    return [[(int(he[r]), bool(hb[r]), int(start[r])) for r in loop]
            for loop in ordered]


def _simple(loops, normal, where, linear) -> bool:
    """Whether the loops, laid flat on their plane, keep clear of each
    other and of themselves: no two sides cross, touch or run along each
    other except where one ends and the next begins."""
    starts = np.array([s for loop in loops for _e, _b, s in loop])
    nexts = np.array([loop[(k + 1) % len(loop)][2] for loop in loops
                      for k in range(len(loop))])
    u = np.cross(normal, [1.0, 0.0, 0.0])
    if np.linalg.norm(u) < 0.5:
        u = np.cross(normal, [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    p = np.stack([where[starts] @ u, where[starts] @ v], axis=1)
    q = np.stack([where[nexts] @ u, where[nexts] @ v], axis=1)
    n = len(p)
    i, j = np.triu_indices(n, 1)
    # sides that share a corner meet there by right
    meet = (starts[i] == starts[j]) | (starts[i] == nexts[j]) \
        | (nexts[i] == starts[j]) | (nexts[i] == nexts[j])
    i, j = i[~meet], j[~meet]
    if not len(i):
        return True
    d = q - p
    length = np.maximum(np.linalg.norm(d, axis=1), 1e-300)

    def side(a, b, at):
        """Signed distance of `at` from the line of side a, in its units."""
        return (d[a, 0] * (at[:, 1] - p[a, 1])
                - d[a, 1] * (at[:, 0] - p[a, 0])) / length[a]

    def sign(x):
        return np.where(x > linear, 1, np.where(x < -linear, -1, 0))

    o1, o2 = sign(side(i, j, p[j])), sign(side(i, j, q[j]))
    o3, o4 = sign(side(j, i, p[i])), sign(side(j, i, q[i]))
    if ((o1 * o2 < 0) & (o3 * o4 < 0)).any():
        return False                      # two sides cross

    def within(a, at):
        """Whether `at`, on side a's line, lies between its ends."""
        t = ((at[:, 0] - p[a, 0]) * d[a, 0]
             + (at[:, 1] - p[a, 1]) * d[a, 1]) / length[a]
        return (t > -linear) & (t < length[a] + linear)

    touch = ((o1 == 0) & within(i, p[j])) | ((o2 == 0) & within(i, q[j])) \
        | ((o3 == 0) & within(j, p[i])) | ((o4 == 0) & within(j, q[i]))
    return not touch.any()


def _edge_chains(ne, nv, ends, where, vslack, interior, he, hf, label):
    """Runs of edges that are one straight line between the same faces,
    meeting at corners nothing else comes to: ([(end, end)] per run,
    run of each edge or -1, which corners go)."""
    chain_of = np.full(ne, -1, np.int64)
    gone = np.zeros(nv, bool)
    counts = np.bincount(he, minlength=ne)
    # an edge only faces that went had is gone with them
    alive = np.nonzero(~interior & (counts > 0))[0]
    # the faces either side of an edge, as the merged faces number them
    lo = np.full(ne, -1, np.int64)
    hi = np.full(ne, -1, np.int64)
    order = np.argsort(he, kind="stable")
    firsts = np.searchsorted(he[order], np.arange(ne))
    one = counts >= 1
    lo[one] = label[hf[order[firsts[one]]]]
    two = np.nonzero(counts == 2)[0]
    other = label[hf[order[firsts[two] + 1]]]
    lo[two], hi[two] = np.minimum(lo[two], other), np.maximum(lo[two], other)
    usable = (counts[alive] >= 1) & (counts[alive] <= 2)

    corner = np.concatenate([ends[alive, 0], ends[alive, 1]])
    edge = np.concatenate([alive, alive])
    degree = np.bincount(corner, minlength=nv)
    pick = degree[corner] == 2
    corner, edge = corner[pick], edge[pick]
    by = np.argsort(corner, kind="stable")
    corner, edge = corner[by], edge[by]
    v, e1, e2 = corner[0::2], edge[0::2], edge[1::2]
    if not len(v):
        return [], chain_of, gone
    ok = (e1 != e2) & (lo[e1] == lo[e2]) & (hi[e1] == hi[e2])
    ok &= np.isin(e1, alive[usable]) & np.isin(e2, alive[usable])
    far1 = np.where(ends[e1, 0] == v, ends[e1, 1], ends[e1, 0])
    far2 = np.where(ends[e2, 0] == v, ends[e2, 1], ends[e2, 0])
    d1, d2 = where[far1] - where[v], where[far2] - where[v]
    span = np.linalg.norm(where[far2] - where[far1], axis=1)
    off = np.linalg.norm(np.cross(d1, d2), axis=1) / np.maximum(span, 1e-300)
    ok &= (off <= vslack[v]) & (np.einsum("ij,ij->i", d1, d2) < 0)
    v, e1, e2 = v[ok], e1[ok], e2[ok]
    if not len(v):
        return [], chain_of, gone
    gone[v] = True
    run = _components(ne, e1, e2)
    in_run = np.zeros(ne, bool)
    in_run[e1] = in_run[e2] = True
    chains = []
    numbers = {}
    for r in np.unique(run[in_run]).tolist():
        members = np.nonzero(run == r)[0]
        corners = np.unique(ends[members].reshape(-1))
        inner = corners[gone[corners]]
        tips = corners[~gone[corners]]
        if len(tips) != 2:
            raise _Unmergeable
        a, b = where[tips[0]], where[tips[1]]
        run_dir = (b - a) / np.linalg.norm(b - a)
        rel = where[inner] - a
        off = np.linalg.norm(rel - np.outer(rel @ run_dir, run_dir), axis=1)
        if (off > vslack[inner]).any():
            gone[inner] = False           # bowed: the edges stay apart
            continue
        numbers[r] = len(chains)
        chains.append((int(tips[0]), int(tips[1])))
        chain_of[members] = numbers[r]
    return chains, chain_of, gone


def _keep_closed(before, after):
    """A shell that was closed is closed still: ReShape builds new shells
    without asking."""
    old = TopExp_Explorer(before, occ.TopAbs_ShapeEnum.TopAbs_SHELL)
    new = TopExp_Explorer(after, occ.TopAbs_ShapeEnum.TopAbs_SHELL)
    while old.More() and new.More():
        shell = new.Current()
        if old.Current().Closed():
            shell.Closed(True)
        old.Next()
        new.Next()


def merged_display(mesh, merged: Merged):
    """The display mesh of the shape before, renumbered for the merged
    one: the same triangles, its faces counted anew, and its lines less the
    seams that went. None when the mesh does not count the old shape's
    faces and edges, which tessellate then draws afresh."""
    from .tessellate import DisplayMesh
    faces = np.asarray(mesh.face_of_triangle)
    lines = np.asarray(mesh.edge_of_segment)
    if len(faces) != len(mesh.triangles) or not len(faces) \
            or len(lines) != len(mesh.local_edges) \
            or faces.min() < 0 or faces.max() >= len(merged.face_map) \
            or (len(lines) and (lines.min() < 0
                                or lines.max() >= len(merged.edge_map))):
        return None
    out = DisplayMesh()
    out.origin = np.array(mesh.origin, copy=True)
    out._far = mesh.far
    out.local = mesh.local
    out.normals = mesh.normals
    out.curvature = mesh.curvature
    out.has_curvature = mesh.has_curvature
    out.local_isos = mesh.local_isos
    out.local_points = mesh.local_points
    # the triangles of faces that went, inside two bodies, go with them
    renamed = merged.face_map[faces]
    shown = renamed >= 0
    out.triangles = (mesh.triangles if shown.all()
                     else mesh.triangles[shown])
    out.face_of_triangle = renamed[shown].astype(np.int32)
    renumbered = merged.edge_map[lines]
    kept = np.nonzero(renumbered >= 0)[0]
    kept = kept[np.argsort(renumbered[kept], kind="stable")]
    out.local_edges = mesh.local_edges[kept]
    out.edge_of_segment = renumbered[kept].astype(np.int32)
    return out
