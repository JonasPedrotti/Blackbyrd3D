"""Wavefront OBJ import/export.

Export tessellates BREP shapes to meshes. Import produces mesh-backed
scene entries by building OCCT faces from triangles (kept lightweight:
one sewn shell per OBJ object).
"""

from __future__ import annotations

import numpy as np

from ..core import geometry, occ
from ..core.tessellate import tessellate


def export_obj(named_shapes: list, path: str):
    """named_shapes: [(name, TopoDS_Shape)] or [(name, shape, color)]"""
    import os
    lines = ["# Blackbyrd3D OBJ export"]
    mtl_lines = []
    mtl_path = os.path.splitext(path)[0] + ".mtl"
    has_colors = any(len(t) > 2 for t in named_shapes)
    if has_colors:
        lines.append(f"mtllib {os.path.basename(mtl_path)}")
    v_offset = 1
    for entry in named_shapes:
        name, shape = entry[0], entry[1]
        color = entry[2] if len(entry) > 2 else None
        mesh = tessellate(shape)
        if not mesh.has_faces:
            continue
        safe = name.replace(" ", "_")
        lines.append(f"o {safe}")
        if color is not None:
            mtl_lines.extend([
                f"newmtl {safe}_mat",
                f"Kd {color[0]:.4g} {color[1]:.4g} {color[2]:.4g}",
                "Ka 0 0 0", "Ks 0.05 0.05 0.05", "Ns 32", "",
            ])
            lines.append(f"usemtl {safe}_mat")
        for v in mesh.vertices:
            lines.append(f"v {v[0]:.15g} {v[1]:.15g} {v[2]:.15g}")
        for n in mesh.normals:
            lines.append(f"vn {n[0]:.6g} {n[1]:.6g} {n[2]:.6g}")
        for t in mesh.triangles:
            a, b, c = (int(i) + v_offset for i in t)
            lines.append(f"f {a}//{a} {b}//{b} {c}//{c}")
        v_offset += len(mesh.vertices)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if has_colors and mtl_lines:
        with open(mtl_path, "w", encoding="utf-8") as f:
            f.write("\n".join(mtl_lines) + "\n")


def import_obj(path: str, as_mesh: bool = True) -> list:
    """Returns [(name, shape)] — native MeshShape objects by default
    (instant), or sewn BREP shells with as_mesh=False."""
    verts: list = []
    # Keyed by (object number, name), not name: every `o` line starts a new
    # object even when its name repeats, which copies of one part always do,
    # while a `g` name met again inside the same object adds to that group.
    groups: dict[tuple[int, str], list] = {}
    obj_no = 0
    current = (obj_no, "obj")
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "v":
                verts.append([float(x) for x in parts[1:4]])
            elif parts[0] == "o" and len(parts) > 1:
                obj_no += 1
                current = (obj_no, parts[1])
            elif parts[0] == "g" and len(parts) > 1:
                current = (obj_no, parts[1])
            elif parts[0] == "f":
                idx = []
                for token in parts[1:]:
                    i = int(token.split("/")[0])
                    idx.append(i - 1 if i > 0 else len(verts) + i)
                # fan-triangulate polygons
                for k in range(1, len(idx) - 1):
                    groups.setdefault(current, []).append(
                        (idx[0], idx[k], idx[k + 1]))

    va = np.asarray(verts, float)
    out = []
    for (_obj_no, name), tris in groups.items():
        if as_mesh:
            from ..core.mesh import MeshShape
            # compact vertices used by this group
            t = np.asarray(tris, np.int64)
            used = np.unique(t)
            remap = np.zeros(len(va), np.int64)
            remap[used] = np.arange(len(used))
            out.append((name, MeshShape(va[used], remap[t])))
        else:
            shell = _shell_from_triangles(va, tris)
            if shell is not None:
                out.append((name, shell))
    return out


def _shell_from_triangles(verts: np.ndarray, tris: list,
                          tolerance: float = 1e-6,
                          progress=None) -> object | None:
    """One shell of planar faces, built with shared vertices and edges.

    Points closer than `tolerance` are welded first, so neighbouring
    triangles share their edges without sewing, which took minutes on
    meshes of a hundred thousand triangles."""
    from OCP.BRep import BRep_Builder
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.TopoDS import TopoDS_Face, TopoDS_Shell, TopoDS_Vertex, TopoDS_Wire
    from OCP.Geom import Geom_Plane
    from OCP.gp import gp_Dir, gp_Pnt

    verts = np.asarray(verts, float).reshape(-1, 3)
    tris = np.asarray(tris, np.int64).reshape(-1, 3)
    if not len(tris) or not len(verts):
        return None
    keys = np.round(verts / tolerance).astype(np.int64)
    _, first, weld = np.unique(keys, axis=0, return_index=True,
                               return_inverse=True)
    points = verts[first]
    tris = weld.reshape(-1)[tris]

    p = points[tris]
    normals = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    sides = np.linalg.norm(p - np.roll(p, -1, axis=1), axis=2).max(axis=1)
    keep = ((tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2])
            & (tris[:, 0] != tris[:, 2]) & (lengths > 1e-12 * sides ** 2))
    tris, normals = tris[keep], normals[keep] / lengths[keep, None]
    if not len(tris):
        return None

    ends = np.stack([tris, np.roll(tris, -1, axis=1)], axis=2)  # (M,3,2)
    lo, hi = ends.min(axis=2), ends.max(axis=2)
    pairs, edge_of = np.unique(np.stack([lo, hi], axis=2).reshape(-1, 2),
                               axis=0, return_inverse=True)
    edge_of = edge_of.reshape(-1, 3)
    flipped = ends[:, :, 0] != lo

    builder = BRep_Builder()
    vertices = [None] * len(points)
    for i in np.unique(pairs):
        v = vertices[i] = TopoDS_Vertex()
        builder.MakeVertex(v, gp_Pnt(*points[i]), tolerance)
    report = progress or (lambda fraction, message="": None)
    total = len(pairs) + len(tris)
    edges = []
    for k, (a, b) in enumerate(pairs.tolist()):
        if not k % 2000:
            report(k / total, "Building edges")
        edges.append(BRepBuilderAPI_MakeEdge(vertices[a], vertices[b]).Edge())
    reversed_edges = [e.Reversed() for e in edges]

    shell = TopoDS_Shell()
    builder.MakeShell(shell)
    for k, (t, ids, flip, n) in enumerate(zip(
            tris.tolist(), edge_of.tolist(), flipped.tolist(),
            normals.tolist())):
        if not k % 2000:
            report((len(pairs) + k) / total, "Building faces")
        wire = TopoDS_Wire()
        builder.MakeWire(wire)
        for k in range(3):
            builder.Add(wire, reversed_edges[ids[k]] if flip[k]
                        else edges[ids[k]])
        wire.Closed(True)
        face = TopoDS_Face()
        builder.MakeFace(face, Geom_Plane(gp_Pnt(*points[t[0]]),
                                          gp_Dir(*n)), tolerance)
        builder.Add(face, wire)
        builder.Add(shell, face)
    shell.Closed(_is_closed(pairs, edge_of))
    return shell


def _is_closed(pairs: np.ndarray, edge_of: np.ndarray) -> bool:
    """Whether every edge is shared by exactly two triangles."""
    counts = np.bincount(edge_of.reshape(-1), minlength=len(pairs))
    return bool(len(counts)) and bool((counts == 2).all())
