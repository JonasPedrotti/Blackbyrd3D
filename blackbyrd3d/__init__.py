"""Blackbyrd3D — an open-source NURBS modeller for Linux."""

import os
import re


def _read_version() -> str:
    """pyproject.toml is the one place the version is written. A checkout
    reads it directly, so an editable install never reports a stale number;
    an installed or bundled build reads the package metadata instead."""
    pyproject = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "pyproject.toml")
    try:
        with open(pyproject, encoding="utf-8") as fh:
            text = fh.read()
        if re.search(r'^name = "blackbyrd3d"$', text, re.MULTILINE):
            found = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
            if found:
                return found.group(1)
    except OSError:
        pass
    try:
        from importlib.metadata import version
        return version("blackbyrd3d")
    except Exception:                                     # noqa: BLE001
        return "0+unknown"


__version__ = _read_version()


def version_line() -> str:
    """What every entry point prints for ``--version``.

    Here rather than in one of them because they all have to agree, and
    because this module is the only thing cheap enough to import when the
    build you are questioning may not survive importing anything else.
    """
    return f"Blackbyrd3D {__version__}"
