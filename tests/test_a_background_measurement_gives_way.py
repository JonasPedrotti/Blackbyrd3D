"""A big object is measured on a thread of its own, and that thread shared
the interpreter with the merge that followed: the merge's card stood still
for a second at a time, and once the merge was done the old object's area
went on being worked out for nobody. The measurement now waits while the
interface thread runs a job behind a card, and stops when the drawing it
was measuring has changed."""

import threading
import time

import numpy as np
import pytest

from blackbyrd3d.core import occ
from blackbyrd3d.fileio.obj import _shell_from_triangles


def _many_triangles(n=60):
    pts, tris = [], []
    for i in range(n + 1):
        for j in range(n + 1):
            pts.append((i, j, 0.3 * np.sin(i) * np.cos(j)))
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            tris += [(a, a + n + 1, a + n + 2), (a, a + n + 2, a + 1)]
    return _shell_from_triangles(np.array(pts, float), tris)


def _area(shape):
    # measured, not the area the converter already knows
    return occ.surface_properties(shape).Mass()


def _on_a_thread(fn):
    out = {}

    def run():
        try:
            out["value"] = fn()
        except Exception as exc:                              # noqa: BLE001
            out["error"] = exc
    t = threading.Thread(target=run)
    t.start()
    return t, out


def test_a_measurement_nobody_wants_stops():
    shell = _many_triangles()

    def measure():
        with occ.wanted_while(lambda: False):
            return _area(shell)
    t, out = _on_a_thread(measure)
    t.join(30)
    assert isinstance(out.get("error"), occ.Superseded)


def test_a_wanted_measurement_finishes():
    shell = _many_triangles()
    expected = _area(shell)

    def measure():
        with occ.wanted_while(lambda: True):
            return _area(shell)
    t, out = _on_a_thread(measure)
    t.join(30)
    assert out["value"] == pytest.approx(expected)


def test_a_measurement_waits_for_the_job_in_front():
    shell = _many_triangles()
    with occ.foreground():
        t, out = _on_a_thread(lambda: _area(shell))
        time.sleep(0.5)
        assert t.is_alive() and not out, "it waits its turn"
    t.join(30)
    assert out["value"] > 0


def test_the_interface_thread_never_waits_on_itself():
    with occ.foreground():
        assert _area(_many_triangles(10)) > 0
