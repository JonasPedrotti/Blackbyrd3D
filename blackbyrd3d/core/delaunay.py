"""Delaunay triangulation of points seen from above, for Wyrm's Delaunay
Mesh: points put in one by one and edges flipped, fast enough for tens of
thousands of points without pulling in a library for it."""

from __future__ import annotations

import numpy as np


class DelaunayError(ValueError):
    pass


def triangulate(xy) -> np.ndarray:
    """The Delaunay triangles of points in the plane, as rows of three
    indices into `xy`, each turning anticlockwise."""
    xy = np.asarray(xy, float)
    if len(xy) < 3:
        raise DelaunayError("A mesh needs at least three points")
    out = _insert_all(xy)
    if not len(out):
        raise DelaunayError("The points are all in a line")
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    size = max(float((hi - lo).max()), 1e-9)
    # anticlockwise from above, so the mesh faces up
    a, b, c = (xy[out[:, k]] for k in range(3))
    turn = ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
            - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    flip = turn < 0
    out[flip] = out[flip][:, [0, 2, 1]]
    out = out[np.abs(turn) > 1e-12 * size * size]
    if not len(out):
        raise DelaunayError("The points are all in a line")
    return out


def _insert_all(xy) -> np.ndarray:
    """Every point put in one after the other, each in the triangle a walk
    from the last one finds, then edges flipped until every triangle's
    circle is empty again (Lawson). Taken in a snake through bins, each
    point lands near the one before, so the walks stay short."""
    n = len(xy)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    size = max(float((hi - lo).max()), 1e-9)
    # a triangle round them all, far enough out to hold every circle
    far = size * 100.0
    corners = (lo + hi) / 2 + np.array([[-far, -far], [far, -far], [0.0, far]])
    pts = np.vstack([xy, corners])
    X, Y = pts[:, 0].tolist(), pts[:, 1].tolist()
    bins = max(1, int(round(n ** 0.25)))
    gx = np.minimum(((xy[:, 0] - lo[0]) / size * bins).astype(int), bins - 1)
    gy = np.minimum(((xy[:, 1] - lo[1]) / size * bins).astype(int), bins - 1)
    snake = np.where(gy % 2 == 0, gx, bins - 1 - gx)
    order = np.lexsort((snake, gy)).tolist()
    # triangle t has its corners anticlockwise at V[3t:3t+3]; N[3t+i] is
    # the triangle across its edge from corner i to corner i+1, -1 if none
    V = [n, n + 1, n + 2]
    N = [-1, -1, -1]

    def left_of(a, b, px, py):
        return (X[b] - X[a]) * (py - Y[a]) - (Y[b] - Y[a]) * (px - X[a])

    def in_circle(a, b, c, px, py):
        adx, ady = X[a] - px, Y[a] - py
        bdx, bdy = X[b] - px, Y[b] - py
        cdx, cdy = X[c] - px, Y[c] - py
        return ((adx * adx + ady * ady) * (bdx * cdy - cdx * bdy)
                - (bdx * bdx + bdy * bdy) * (adx * cdy - cdx * ady)
                + (cdx * cdx + cdy * cdy) * (adx * bdy - bdx * ady)) > 0

    def edge_to(t, u):
        b = 3 * t
        return 0 if N[b] == u else 1 if N[b + 1] == u else 2

    t = 0
    for p in order:
        px, py = X[p], Y[p]
        for _ in range(len(N) + 1):
            b = 3 * t
            for i in range(3):
                if (left_of(V[b + i], V[b + (i + 1) % 3], px, py) < 0
                        and N[b + i] >= 0):
                    t = N[b + i]
                    break
            else:
                break
        else:
            raise DelaunayError("The points could not be meshed")
        # split t into three round p: (a0 a1 p), (a1 a2 p), (a2 a0 p)
        b = 3 * t
        a0, a1, a2 = V[b:b + 3]
        n0, n1, n2 = N[b:b + 3]
        t1 = len(V) // 3
        t2 = t1 + 1
        V[b:b + 3] = [a0, a1, p]
        N[b:b + 3] = [n0, t1, t2]
        V += [a1, a2, p, a2, a0, p]
        N += [n1, t2, t, n2, t, t1]
        if n1 >= 0:
            N[3 * n1 + edge_to(n1, t)] = t1
        if n2 >= 0:
            N[3 * n2 + edge_to(n2, t)] = t2
        # p is corner 2 of each new triangle, facing its edge 0; a
        # neighbour across it whose far corner is in the circle flips it
        waiting = [t, t1, t2]
        while waiting:
            u = waiting.pop()
            bu = 3 * u
            o = N[bu]
            if o < 0:
                continue
            bo = 3 * o
            j = edge_to(o, u)
            q = V[bo + (j + 2) % 3]
            if not in_circle(V[bu], V[bu + 1], p, X[q], Y[q]):
                continue
            v0, v1 = V[bu], V[bu + 1]
            across_v1p, across_pv0 = N[bu + 1], N[bu + 2]
            across_v0q = N[bo + (j + 1) % 3]
            across_qv1 = N[bo + (j + 2) % 3]
            V[bu:bu + 3] = [v0, q, p]
            N[bu:bu + 3] = [across_v0q, o, across_pv0]
            V[bo:bo + 3] = [q, v1, p]
            N[bo:bo + 3] = [across_qv1, across_v1p, u]
            if across_v0q >= 0:
                N[3 * across_v0q + edge_to(across_v0q, o)] = u
            if across_v1p >= 0:
                N[3 * across_v1p + edge_to(across_v1p, u)] = o
            waiting += [u, o]
    tris = np.array(V, dtype=np.int64).reshape(-1, 3)
    return tris[(tris < n).all(axis=1)]


def unique_points(points, tolerance=1e-9) -> np.ndarray:
    """Points with any that stand on another, seen from above, left out."""
    pts = np.asarray(points, float)
    keys = np.round(pts[:, :2] / max(tolerance, 1e-15)).astype(np.int64)
    _, first = np.unique(keys, axis=0, return_index=True)
    return pts[np.sort(first)]


def inside_outline(xy, rim) -> np.ndarray:
    """Which points lie inside a closed outline given as its segments, seen
    from above: a ray to the right crosses it an odd number of times."""
    xy = np.asarray(xy, float)
    a, b = rim[:, 0], rim[:, 1]                     # (K, 2) each
    px, py = xy[:, 0][:, None], xy[:, 1][:, None]   # (N, 1)
    ay, by = a[:, 1][None, :], b[:, 1][None, :]
    ax, bx = a[:, 0][None, :], b[:, 0][None, :]
    spans = (ay > py) != (by > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        cross = ax + (py - ay) * (bx - ax) / (by - ay)
    hits = spans & (px < cross)
    return hits.sum(axis=1) % 2 == 1
