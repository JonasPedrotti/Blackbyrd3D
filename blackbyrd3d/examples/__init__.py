"""The example models offered on the welcome screen, and the example
graphs on Wyrm's start page.

Built by packaging/examples/make_examples.py. They open as copies: Save
asks where to put one, so the file shipped with the program stays as it is.
"""

from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))

# file, title, what it shows; each opens in the display it was saved in
EXAMPLES = (
    ("cabin.byrd", "Cabin", "3D planning in metres"),
    ("detail.byrd", "Glazing detail", "2D drafting, lineweights, hatches"),
    ("stool.byrd", "Stool", "Workshop sheet, live views"),
    ("urban.byrd", "Urban block", "Plaster colour, ambient occlusion"),
)

# file, title, what it shows; a graph that needs nothing from the model
WYRM_EXAMPLES = (
    ("example_file.wyrm", "Example file",
     "Terrain, contours, height tags"),
)


def _there(listed) -> list[tuple[str, str, str]]:
    out = []
    for name, title, about in listed:
        path = os.path.join(_HERE, name)
        if os.path.exists(path):
            out.append((path, title, about))
    return out


def examples() -> list[tuple[str, str, str]]:
    """(path, title, description) of each example that is there."""
    return _there(EXAMPLES)


def wyrm_examples() -> list[tuple[str, str, str]]:
    return _there(WYRM_EXAMPLES)


def is_example(path: str) -> bool:
    return os.path.dirname(os.path.abspath(path)) == _HERE

