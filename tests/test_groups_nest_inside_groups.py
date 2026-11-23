"""A group made of groups keeps them inside it: a click selects the
outermost, Ungroup ends only that one, and files carry every level."""

from blackbyrd3d import fileio
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene, group_chain, outer_group
from blackbyrd3d.fileio.native import load_scene, save_scene
from blackbyrd3d.fileio.rhino import export_3dm


def _group(proc, selection, objects):
    selection.set([o.id for o in objects])
    assert proc.run("group")
    assert not proc.busy


def _boxes(scene, count):
    return [scene.add(g.make_box((6 * i, 0, 0), 2, 2, 2), name=f"B{i}")
            for i in range(count)]


def test_grouping_a_group_with_more_puts_one_group_round_it(env):
    scene, selection, _history, _ctx, proc = env
    a, b, c = _boxes(scene, 3)
    _group(proc, selection, [a, b])
    inner = scene.get(a.id).group_id
    _group(proc, selection, [a, b, c])
    chain_a = group_chain(scene.get(a.id).group_id)
    assert chain_a[1:] == [inner]
    assert group_chain(scene.get(b.id).group_id) == chain_a
    assert group_chain(scene.get(c.id).group_id) == chain_a[:1]
    assert sorted(scene.expand_group_ids([c.id])) == sorted(
        [a.id, b.id, c.id])


def test_ungroup_ends_the_outermost_and_leaves_the_one_inside(env):
    scene, selection, _history, _ctx, proc = env
    a, b, c = _boxes(scene, 3)
    _group(proc, selection, [a, b])
    inner = scene.get(a.id).group_id
    _group(proc, selection, [a, b, c])
    selection.set([a.id, b.id, c.id])
    assert proc.run("ungroup")
    assert scene.get(a.id).group_id == inner == scene.get(b.id).group_id
    assert scene.get(c.id).group_id is None
    assert sorted(scene.expand_group_ids([a.id])) == sorted([a.id, b.id])


def _nested(scene):
    """Two boxes in a group, inside a group with a third."""
    a, b, c, loose = _boxes(scene, 4)
    scene.update(a.id, group_id="outer\x1finner")
    scene.update(b.id, group_id="outer\x1finner")
    scene.update(c.id, group_id="outer")
    return a, b, c, loose


def _shape_of_groups(scene):
    """Each object's groups by how many objects each holds, by name."""
    members = {}
    for o in scene.all():
        for gid in group_chain(o.group_id):
            members.setdefault(gid, set()).add(o.name)
    return {o.name: [len(members[gid]) for gid in group_chain(o.group_id)]
            for o in scene.all()}


def test_a_rhino_file_keeps_every_level(tmp_path):
    scene = Scene()
    _nested(scene)
    path = str(tmp_path / "nested.3dm")
    export_3dm(scene, path)
    back = Scene()
    fileio.import_file(back, path)
    assert _shape_of_groups(back) == {"B0": [3, 2], "B1": [3, 2],
                                      "B2": [3], "B3": []}
    by_name = {o.name: o for o in back.all()}
    assert len(back.expand_group_ids([by_name["B2"].id])) == 3
    assert outer_group(by_name["B3"].group_id) is None


def test_a_byrd_file_keeps_every_level(tmp_path):
    scene = Scene()
    _nested(scene)
    path = str(tmp_path / "nested.byrd")
    save_scene(scene, path)
    back = Scene()
    load_scene(back, path)
    assert _shape_of_groups(back) == _shape_of_groups(scene)
