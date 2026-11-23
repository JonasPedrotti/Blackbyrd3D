"""Custom Preview: geometry shown in the model in a colour of its own."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ... import geometry as g
from . import COMPONENTS, Component, Result
from ..kinds import (
    Colour, GeometryGroup, Port, coerce, fits, is_shape, kind_said, said_of,
)


# the colour the graph's own preview is drawn in
PREVIEW_COLOUR = "#9e8cff"


@dataclass(frozen=True)
class Style:
    """How a Custom Preview draws a shape: its colour, how opaque it is,
    0 not seen at all to 1 hiding what lies behind, a curve's width in
    pixels, None for the hairline other shapes' edges are drawn with, and
    whether text sits on a background."""
    colour: Colour
    opacity: float = 1.0
    thickness: float | None = 2.0
    background: bool = True


def _text(shape) -> bool:
    from ...text_object import TextShape
    return isinstance(shape, TextShape)


def _line(shape) -> bool:
    return (is_shape(shape) and not _text(shape)
            and g.shape_kind(shape) == "curve")


def _shapes(value) -> list:
    return value.flat() if isinstance(value, GeometryGroup) else [value]


def _incoming(graph, node, results) -> list:
    tree, _wired = graph.input_values(node.id, _GEOMETRY, results)
    return [s for v in tree.items for s in _shapes(v) if is_shape(s)]


def _wants_extra(graph, node, results):
    shapes = _incoming(graph, node, results)
    wanted = []
    if any(_line(s) for s in shapes):
        wanted.append("T")
    if any(_text(s) for s in shapes):
        wanted.append("B")
    return wanted


def _custom_preview(graph, node, scene, results) -> Result:
    comp = COMPONENTS[node.key]
    values = {}
    for port in comp.inputs + comp.extra:
        tree, _wired = graph.input_values(node.id, port, results)
        values[port.name] = [coerce(port.kind, v) for v in tree.items]
    if not values["G"]:
        return Result({}, "warning", "Connect G")
    for name in ("C", "O", "T", "B"):
        port = next(p for p in comp.inputs + comp.extra if p.name == name)
        if not values[name]:
            values[name] = [port.default]
        for value in values[name]:
            if not fits(port.kind, value):
                return Result({}, "error", f"Custom Preview {name} takes "
                              f"{kind_said(port.kind)}, not {said_of(value)}")
    styled = []
    for i, item in enumerate(values["G"]):
        at = {name: values[name][min(i, len(values[name]) - 1)]
              for name in ("C", "O", "T", "B")}
        if not 0.0 <= float(at["O"]) <= 1.0:
            return Result({}, "error", "Opacity goes from 0 to 1")
        if float(at["T"]) <= 0:
            return Result({}, "error", "Thickness must be more than 0")
        style = Style(at["C"], float(at["O"]), float(at["T"]), bool(at["B"]))
        shapes = _shapes(item)
        if not all(is_shape(s) for s in shapes):
            return Result({}, "error", "Custom Preview G takes geometry, "
                          f"not {said_of(item)}")
        for shape in shapes:
            drawn = (shape.with_background(style.background)
                     if _text(shape) else shape)
            own = style if _line(shape) else replace(style, thickness=None)
            styled.append((drawn, own, shape))
    result = Result({})
    result.styled = styled
    return result


_GEOMETRY = Port("G", "geometry", label="Geometry",
                 description="What is shown in the style")


COMPONENTS["custom_preview"] = Component(
    "custom_preview", "Custom Preview", "Display",
    inputs=(_GEOMETRY,
            Port("C", "colour", Colour.from_hex(PREVIEW_COLOUR),
                 label="Colour", description="The colour it is shown in"),
            Port("O", "number", 1.0, label="Opacity",
                 description="How opaque it is, from 0, not seen at all, "
                             "to 1, hiding what lies behind")),
    extra=(Port("T", "number", 2.0, label="Thickness",
                description="How wide its lines are drawn, in pixels"),
           Port("B", "boolean", True, label="Background",
                description="Whether text sits on a background that hides "
                            "what lies behind it")),
    wants_extra=_wants_extra, icon="custompreview", made=_custom_preview,
    description="Shows geometry in the model in a colour of its own, "
                "as opaque as asked; Thickness comes in for "
                "lines, Background for text")
