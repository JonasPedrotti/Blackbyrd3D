"""Meshtobrep builds its shell from the mesh's own shared corners and
edges instead of sewing loose triangles, which took over a minute for a
hundred thousand of them and hung the window until Windows closed it. The
shell is then drawn straight off its triangles, as the slow way drew it."""

import numpy as np
import pytest

import blackbyrd3d.commands  # registers all commands  # noqa: F401
from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core import tessellate as T
from blackbyrd3d.core.history import History
from blackbyrd3d.core.mesh import MeshShape, brep_from_mesh
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.fileio.obj import _shell_from_triangles

CUBE_V = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                   [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
CUBE_T = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                   [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                   [1, 2, 6], [1, 6, 5], [3, 0, 4], [3, 4, 7]])


def test_a_closed_mesh_becomes_one_closed_valid_shell():
    shell = brep_from_mesh(MeshShape(CUBE_V, CUBE_T))
    assert g.is_valid(shell)
    assert shell.Closed()
    assert g.surface_area(shell) == pytest.approx(6.0)
    assert len(g.edges_of(shell)) == 18, "neighbours share their edges"


def test_loose_triangles_are_welded_by_position():
    soup = CUBE_V[CUBE_T].reshape(-1, 3)
    shell = _shell_from_triangles(soup, np.arange(len(soup)).reshape(-1, 3))
    assert shell.Closed()
    assert len(g.edges_of(shell)) == 18


def test_degenerate_triangles_are_left_out():
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [2, 0, 0]], float)
    shell = _shell_from_triangles(v, [(0, 1, 2), (0, 1, 3), (1, 1, 2)])
    assert g.surface_area(shell) == pytest.approx(0.5)
    assert _shell_from_triangles(v, [(0, 1, 3)]) is None


@pytest.mark.parametrize("move", [
    lambda s: s,
    lambda s: g.rotate(g.translate(s, (5, 1, 2)), (0, 0, 0), (1, 1, 0), 33),
    lambda s: g.mirror(s, (0, 0, 0), (1, 0, 0)),
])
def test_a_triangle_shell_draws_as_the_slow_way_drew_it(move, monkeypatch):
    shell = move(brep_from_mesh(MeshShape(CUBE_V, CUBE_T)))
    quick = T.tessellate(shell)
    monkeypatch.setattr(T, "_triangle_faces_mesh", lambda s: None)
    slow = T.tessellate(shell)

    def facing(m):
        p = m.vertices[m.triangles]
        w = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        return (0.5 * np.linalg.norm(w, axis=1).sum(),
                bool((np.einsum("ij,ij->i", w,
                                m.normals[m.triangles[:, 0]]) > 0).all()))

    assert len(quick.triangles) == len(slow.triangles) == 12
    assert facing(quick) == pytest.approx(facing(slow))
    assert facing(quick)[1], "normals face the way the triangles wind"
    assert sorted(quick.face_of_triangle) == sorted(slow.face_of_triangle)
    assert (quick.edge_of_segment == slow.edge_of_segment).all()
    assert np.allclose(quick.edge_segments, slow.edge_segments)


def test_the_converter_hands_over_the_display_tessellate_would_make():
    rng = np.random.default_rng(3)
    v = rng.random((40, 3))
    t = np.array([rng.choice(40, 3, replace=False) for _ in range(60)])
    shell, made = brep_from_mesh(MeshShape(v, t), display=True)
    drawn = T.tessellate(shell)
    assert np.allclose(made.vertices, drawn.vertices)
    assert np.allclose(made.normals, drawn.normals, atol=1e-6)
    assert (made.triangles == drawn.triangles).all()
    assert (made.face_of_triangle == drawn.face_of_triangle).all()
    assert np.allclose(made.edge_segments, drawn.edge_segments)
    assert (made.edge_of_segment == drawn.edge_of_segment).all()


def test_other_shapes_still_mesh_the_usual_way():
    assert T._triangle_faces_mesh(g.make_box((0, 0, 0), 1, 1, 1)) is None


def test_the_command_converts_without_a_window():
    scene = Scene()
    sel = SelectionManager(scene)
    proc = CommandProcessor(CommandContext(scene, sel, History(scene)))
    obj = scene.add(MeshShape(CUBE_V, CUBE_T))
    sel.set([obj.id])
    proc.run("meshtobrep")
    assert not proc.busy
    assert scene.get(obj.id).kind == "surface"
    assert scene.get(obj.id).mesh_ready
