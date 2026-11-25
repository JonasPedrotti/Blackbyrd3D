"""The command reference on the documentation site lists every command with
a real description, and stays in step with the commands the app has."""

from __future__ import annotations

import importlib.util
import os

from blackbyrd3d.commands.base import all_commands

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


def _generator():
    spec = importlib.util.spec_from_file_location(
        "gen_commands", os.path.join(DOCS, "gen_commands.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_command_says_what_it_does():
    bare = sorted(cd.name for cd in all_commands()
                  if cd.fn.__module__.startswith("blackbyrd3d.")
                  and not (cd.fn.__doc__ or "").strip())
    assert bare == []


def test_the_published_reference_matches_the_commands():
    gen = _generator()
    with open(gen.OUT, encoding="utf-8") as f:
        published = f.read()
    assert published == gen.render(), (
        "docs/reference/commands.md is out of date, "
        "run docs/gen_commands.py")
