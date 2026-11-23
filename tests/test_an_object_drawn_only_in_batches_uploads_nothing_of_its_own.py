"""An object that can go in a batch is nearly always drawn in one, and its
own buffers and arrays, one set per object and viewport, were most of
opening a .3dm of thousands of small curves. It makes them on its first
draw of its own, and until then holds only what batching asks of it."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.tessellate import tessellate
from blackbyrd3d.ui import gpu_share, viewport as vp


@pytest.fixture
def uploads(monkeypatch):
    gpu_share.reset()
    monkeypatch.setattr(vp, "_current_share_group", lambda: None)
    bound = []
    monkeypatch.setattr(vp.GL, "glGetIntegerv", lambda _name: 7)
    monkeypatch.setattr(vp.GL, "glBindVertexArray", bound.append)
    monkeypatch.setattr(vp.GL, "glBindBuffer", lambda *_: None)
    made = []

    def build(mesh, dash):
        made.append(mesh)
        return SimpleNamespace(cloud_levels=None, cloud_colored=False,
                               anchor=vp.mesh_anchor(mesh), cloud_count=0,
                               tri_count=0, line_count=0, iso_count=0,
                               nbytes=0, release=lambda: None)

    monkeypatch.setattr(vp, "_MeshBuffers", build)
    yield SimpleNamespace(made=made, bound=bound)
    gpu_share.reset()


def _curve_mesh():
    return tessellate(g.make_line((0, 0, 0), (10, 0, 0)))


def test_batching_asks_nothing_that_uploads(uploads):
    mesh = _curve_mesh()
    assert vp._batchable(mesh, "Continuous")
    gpu = vp._GpuObject(mesh, dash_key="Continuous", lazy=True)
    assert gpu.plain and gpu.tri_count == 0 and gpu.cloud_count == 0
    assert gpu.anchor_xyz is None and gpu.mesh_key == mesh.uid
    assert uploads.made == [] and gpu_share.count() == 0


def test_its_first_own_draw_uploads_it_once(uploads):
    mesh = _curve_mesh()
    gpu = vp._GpuObject(mesh, dash_key="Continuous", lazy=True)
    assert gpu.line_count == 0              # what the stand-in uploaded
    gpu.tri_vao
    assert uploads.made == [mesh] and gpu_share.count() == 1
    # whatever array the draw had bound is bound again afterwards
    assert uploads.bound[-1] == 7
    gpu.release()
    assert gpu_share.count() == 0


def test_one_never_drawn_alone_gives_back_nothing(uploads):
    gpu = vp._GpuObject(_curve_mesh(), dash_key="Continuous", lazy=True)
    gpu.release()
    gpu.forget()
    assert uploads.made == [] and gpu_share.count() == 0


def test_what_cannot_go_in_a_batch_is_not_put_off():
    mesh = _curve_mesh()
    assert not vp._batchable(mesh, "Dashed")
    assert not vp._batchable(
        tessellate(g.make_sphere((0, 0, 0), 5), deflection=0.001),
        "Continuous")
