"""A mesh turned into a Brep is a hundred thousand flat triangles, and
MergeAllCoplanarFaces on one took ShapeUpgrade_UnifySameDomain a minute and
a half with the window frozen. Planes and lines go through core.coplanar
instead: the same faces fused, a valid shape, the picture handed over as it
was and the merged object picked and ready to work with."""

import time

import numpy as np
import pytest

import blackbyrd3d.commands  # registers all commands  # noqa: F401
from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core import coplanar
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core import tessellate as T
from blackbyrd3d.core.history import History
from blackbyrd3d.core.mesh import MeshShape, brep_from_mesh
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.fileio.obj import _shell_from_triangles


def _side(origin, u, v, n):
    """An n by n grid of triangles over the parallelogram origin, u, v."""
    o, u, v = (np.asarray(x, float) for x in (origin, u, v))
    tris = []
    for i in range(n):
        for j in range(n):
            a = o + u * i / n + v * j / n
            b, c, d = a + u / n, a + u / n + v / n, a + v / n
            tris += [(a, b, c), (a, c, d)]
    return tris


def _grid_box(n, size=10.0):
    """A size cube of 12 n^2 triangles, all turned to face outwards."""
    s = size
    sides = [((0, 0, 0), (0, s, 0), (s, 0, 0)),
             ((0, 0, s), (s, 0, 0), (0, s, 0)),
             ((0, 0, 0), (s, 0, 0), (0, 0, s)),
             ((0, s, 0), (0, 0, s), (s, 0, 0)),
             ((0, 0, 0), (0, 0, s), (0, s, 0)),
             ((s, 0, 0), (0, s, 0), (0, 0, s))]
    soup = np.array([t for o, u, v in sides for t in _side(o, u, v, n)])
    flat = soup.reshape(-1, 3)
    tris = np.arange(len(flat)).reshape(-1, 3)
    p = flat[tris]
    w = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    inward = np.einsum("ij,ij->i", w, p.mean(axis=1) - s / 2) < 0
    tris[inward] = tris[inward][:, ::-1]
    return _shell_from_triangles(flat, tris)


def _plate_with_a_hole():
    """A square plate with a square hole, in eight triangles."""
    outer = [(0, 0), (6, 0), (6, 6), (0, 6)]
    inner = [(2, 2), (4, 2), (4, 4), (2, 4)]
    v = np.array([(x, y, 0.0) for x, y in outer + inner])
    t = []
    for k in range(4):
        a, b = k, (k + 1) % 4
        t += [(a, b, 4 + b), (a, 4 + b, 4 + a)]
    return _shell_from_triangles(v, t)


def test_a_converted_box_merges_back_into_six_faces():
    shell = _grid_box(6)
    assert len(g.faces_of(shell)) == 6 * 2 * 36
    merged = coplanar.merge_flat(shell)
    assert merged is not None
    assert len(g.faces_of(merged.shape)) == 6
    assert len(g.edges_of(merged.shape)) == 12, "the cube's edges are whole"
    assert g.is_valid(merged.shape)
    assert merged.shape.Closed()
    assert g.surface_area(merged.shape) == pytest.approx(600.0)


def test_the_merged_box_faces_the_way_the_triangles_did():
    shell = _grid_box(3)
    merged = coplanar.merge_flat(shell)
    drawn = T.tessellate(merged.shape)
    p = drawn.vertices[drawn.triangles]
    w = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    out = np.einsum("ij,ij->i", w, p.mean(axis=1) - 5.0)
    assert (out > 0).all(), "every face still looks out of the box"


def test_a_hole_stays_a_hole():
    merged = coplanar.merge_flat(_plate_with_a_hole())
    faces = g.faces_of(merged.shape)
    assert len(faces) == 1
    from OCP.TopoDS import TopoDS_Iterator
    wires, it = 0, TopoDS_Iterator(faces[0])
    while it.More():
        wires += 1
        it.Next()
    assert wires == 2
    assert g.is_valid(merged.shape)
    assert g.surface_area(merged.shape) == pytest.approx(32.0)


def _folded(rise):
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, rise]], float)
    return _shell_from_triangles(v, [(0, 1, 2), (1, 3, 2)])


def test_a_fold_beyond_the_drawing_tolerance_is_not_flattened():
    merged = coplanar.merge_flat(_folded(5e-3), angle=0.0)
    assert len(g.faces_of(merged.shape)) == 2


def test_a_fold_beyond_the_angle_is_not_flattened():
    rise = np.sqrt(0.5) * np.tan(np.radians(2.0))    # 2 degrees
    merged = coplanar.merge_flat(_folded(rise))
    assert len(g.faces_of(merged.shape)) == 2


def test_triangles_off_flat_within_the_drawing_tolerance_merge():
    merged = coplanar.merge_flat(_folded(4e-4))
    assert len(g.faces_of(merged.shape)) == 1
    assert g.is_valid(merged.shape)


def test_the_tolerance_can_be_given():
    def faces(rise, tolerance):
        merged = coplanar.merge_flat(_folded(rise), tolerance=tolerance,
                                     angle=0.0)
        return len(g.faces_of(merged.shape))
    assert faces(4e-4, 1e-5) == 2
    assert faces(5e-3, 1e-2) == 1


def test_a_long_wall_a_hair_askew_is_one_face():
    """Merge.byrd's facade had a fold of 0.27 degrees across it. Along the
    diagonal of a 200 by 50 wall that puts the far corner 0.23 mm off, far
    past the tolerance, and is flat to the eye all the same."""
    across = 200 * 50 / np.hypot(200, 50)     # corner to the diagonal
    rise = across * np.tan(np.radians(0.27))
    v = np.array([[0, 0, 0], [200, 0, 0], [0, 50, 0], [200, 50, rise]],
                 float)
    shell = _shell_from_triangles(v, [(0, 1, 2), (1, 3, 2)])
    merged = coplanar.merge_flat(shell)
    assert len(g.faces_of(merged.shape)) == 1
    assert g.is_valid(merged.shape)


def test_the_facets_of_a_column_stay_facets():
    tris, pts = [], []
    for k in range(65):
        a = 2 * np.pi * k / 64
        pts += [(np.cos(a), np.sin(a), 0.0), (np.cos(a), np.sin(a), 3.0)]
    for k in range(64):
        i = 2 * k
        tris += [(i, i + 2, i + 3), (i, i + 3, i + 1)]
    merged = coplanar.merge_flat(_shell_from_triangles(np.array(pts), tris))
    assert len(g.faces_of(merged.shape)) == 64


def test_a_gentle_curve_is_not_merged_flat_step_by_step():
    """Each step a hair off its neighbour, but the whole arc bows far more
    than the tolerance: the merged faces have to stay true to it."""
    tris, pts = [], []
    for k in range(41):
        a = 0.004 * k                   # radius 100: 0.4 mm sag per step
        pts += [(100 * np.sin(a), 0.0, 100 * (1 - np.cos(a))),
                (100 * np.sin(a), 5.0, 100 * (1 - np.cos(a)))]
    for k in range(40):
        i = 2 * k
        tris += [(i, i + 2, i + 3), (i, i + 3, i + 1)]
    shell = _shell_from_triangles(np.array(pts), tris)
    merged = coplanar.merge_flat(shell, tolerance=1e-2)
    faces = len(g.faces_of(merged.shape))
    assert 1 < faces < 80
    assert g.is_valid(merged.shape)


def test_curved_shapes_are_left_to_occt():
    assert coplanar.merge_flat(g.make_sphere((0, 0, 0), 2.0)) is None


def test_the_handed_over_display_counts_the_new_faces_and_edges():
    shell = _grid_box(4)
    before = T.tessellate(shell)
    merged = coplanar.merge_flat(shell)
    shown = coplanar.merged_display(before, merged)
    fresh = T.tessellate(merged.shape)
    assert sorted(set(shown.face_of_triangle)) == list(range(6))
    assert sorted(set(shown.edge_of_segment)) == \
        sorted(set(fresh.edge_of_segment)) == list(range(12))

    def area(m):
        p = m.vertices[m.triangles]
        return 0.5 * np.linalg.norm(
            np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1).sum()
    assert area(shown) == pytest.approx(area(fresh))
    # each face's triangles lie where tessellate puts that face
    for f in range(6):
        a = shown.vertices[shown.triangles[shown.face_of_triangle == f]]
        b = fresh.vertices[fresh.triangles[fresh.face_of_triangle == f]]
        assert np.allclose(a.reshape(-1, 3).min(0), b.reshape(-1, 3).min(0))
        assert np.allclose(a.reshape(-1, 3).max(0), b.reshape(-1, 3).max(0))


def test_a_big_converted_mesh_merges_in_seconds():
    shell = _grid_box(40)                     # 19200 triangles
    start = time.perf_counter()
    merged = coplanar.merge_flat(shell)
    assert time.perf_counter() - start < 10.0
    assert len(g.faces_of(merged.shape)) == 6


@pytest.fixture
def env():
    scene = Scene()
    sel = SelectionManager(scene)
    ctx = CommandContext(scene, sel, History(scene))
    return scene, ctx, CommandProcessor(ctx)


def test_the_command_leaves_the_merged_object_picked_and_drawn(env):
    scene, ctx, proc = env
    obj = scene.add(_grid_box(5), name="Converted")
    g.know_area(obj.shape, 600.0)
    obj.mesh
    proc.run("mergeallcoplanarfaces")
    proc.click_object(obj.id)
    proc.finish_selection()
    done = scene.objects[obj.id]
    assert len(g.faces_of(done.shape)) == 6
    assert done.mesh_ready, "the picture came along, nothing to remesh"
    assert set(done.mesh.face_of_triangle.tolist()) == set(range(6))
    assert g.known_area(done.shape) == pytest.approx(600.0)
    assert ctx.selection.ids == [obj.id], "picked, ready for the next step"


def test_the_command_on_a_mesh_converted_with_meshtobrep(env):
    scene, ctx, proc = env
    v = np.array([[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0], [1, 1, 0]],
                 float)
    t = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    obj = scene.add(brep_from_mesh(MeshShape(v, t)), name="Fan")
    proc.run("mergeallcoplanarfaces")
    proc.click_object(obj.id)
    proc.finish_selection()
    done = scene.objects[obj.id]
    assert len(g.faces_of(done.shape)) == 1
    assert len(g.edges_of(done.shape)) == 4
    assert g.surface_area(done.shape) == pytest.approx(4.0)
