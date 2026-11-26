"""Enter, Space and a right-click all submit an empty answer. A prompt that
has nothing to give for it used to say "Expected coordinates" and keep
asking; it ends the command instead, as Esc does."""

import pytest

from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager

import blackbyrd3d.commands  # noqa: F401


@pytest.fixture
def env():
    scene = Scene()
    sel = SelectionManager(scene)
    history = History(scene)
    ctx = CommandContext(scene, sel, history)
    said = []
    ctx.add_echo_listener(said.append)
    return scene, CommandProcessor(ctx), said


DRAWING = ["line", "polyline", "curve", "interpcrv", "circle", "arc",
           "ellipse", "rectangle", "box", "sphere", "cylinder", "cone",
           "torus", "plane", "plane3pt", "srfpt"]


@pytest.mark.parametrize("name", DRAWING)
def test_empty_answer_at_the_first_prompt_ends_the_command(env, name):
    scene, proc, said = env
    proc.run(name)
    assert proc.busy
    proc.provide_text("")
    assert not proc.busy
    assert not list(scene.all())
    assert not any("Expected" in s for s in said)


@pytest.mark.parametrize("name", DRAWING)
def test_empty_answer_after_one_point_ends_the_command(env, name):
    scene, proc, said = env
    proc.run(name)
    proc.provide((0.0, 0.0, 0.0))
    if proc.busy:
        proc.provide_text("")
    assert not proc.busy
    assert not list(scene.all())
    assert not any("Expected" in s for s in said)


def test_enter_at_the_extrude_distance_extrudes_nothing(env):
    """It took a hidden default of 10 and extruded that."""
    from blackbyrd3d.core import geometry as g
    scene, proc, _said = env
    circle = scene.add(g.make_circle((0, 0, 0), 5.0))
    proc.run("extrude")
    proc.click_object(circle.id)
    proc.finish_selection()
    assert proc.busy
    proc.provide_text("")
    assert not proc.busy
    assert [o.id for o in scene.all()] == [circle.id]


def test_enter_still_finishes_a_polyline_that_has_enough_points(env):
    scene, proc, _said = env
    proc.run("polyline")
    proc.provide((0.0, 0.0, 0.0))
    proc.provide((5.0, 0.0, 0.0))
    proc.provide((5.0, 5.0, 0.0))
    proc.provide_text("")
    assert not proc.busy
    assert len(list(scene.all())) == 1
