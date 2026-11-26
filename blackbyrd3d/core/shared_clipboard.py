"""What Copy took, where another Blackbyrd3D window can find it.

Every window is a process of its own, so the objects a copy holds live only
in the one that made it. The system clipboard gets nothing but words (see
MainWindow._claim_clipboard), so the objects themselves go to a file every
window can read. It is written when the window lets go of the focus or
closes, not at the copy: a copy of thousands of objects pasted in the same
window should not pay for turning them all into bytes.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile


def path() -> str:
    override = os.environ.get("BYRD3D_SHARED_CLIPBOARD")
    if override:
        return override
    return os.path.join(tempfile.gettempdir(), "blackbyrd3d", "clipboard.json")


def _write(record: dict):
    target = path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh)
        os.replace(tmp, target)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def announce(words: str, stamp: float):
    """A copy was made here and is not written yet, so no other window
    pastes what an older copy left in the file."""
    _write({"pid": os.getpid(), "stamp": stamp, "words": words,
            "pending": True})


def publish(words: str, stamp: float, clip, layers):
    """Write the copy out in full."""
    from . import geometry as g
    kind, items = clip
    record = {"pid": os.getpid(), "stamp": stamp, "words": words,
              "kind": kind}
    if kind == "model":
        out = []
        for name, shape, layer_id in items:
            try:
                layer = layers.get(layer_id)
                where = {"path": layers.full_path(layer_id),
                         "color": list(layer.color)}
            except KeyError:
                where = None
            out.append({"name": name, "layer": where,
                        "shape": base64.b64encode(
                            g.shape_to_bytes(shape)).decode("ascii")})
        record["items"] = out
    else:
        from .layout import Layout, layouts_to_json, sheet_pools
        holder = Layout()
        pools = sheet_pools(holder)
        for k, obj in items:
            if k in pools:
                pools[k].append(obj)
        record["sheet"] = layouts_to_json([holder])[0]
    _write(record)


# A copy this size takes seconds to read back, so a paste shows its card
# at once rather than after half a second it never gets to.
_BIG_BYTES = 2_000_000


def is_big() -> bool:
    try:
        return os.path.getsize(path()) > _BIG_BYTES
    except OSError:
        return False


def read() -> dict | None:
    try:
        with open(path(), encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def model_items(record: dict, progress=None) -> list:
    """(name, shape, where) for each copied object, where being the path
    and colour of its layer, for layer_for to find or make once the paste
    has taken its undo checkpoint."""
    from . import geometry as g
    out = []
    items = record.get("items", [])
    for i, it in enumerate(items):
        if progress is not None:
            progress(i / len(items), f"Reading object {i + 1} of {len(items)}")
        shape = g.shape_from_bytes(base64.b64decode(it["shape"]))
        out.append((it.get("name", ""), shape, it.get("layer")))
    return out


def sheet_items(record: dict) -> list:
    from .layout import layouts_from_json, sheet_pools
    holder = layouts_from_json([record["sheet"]])[0]
    return [(k, obj) for k, pool in sheet_pools(holder).items()
            for obj in pool]


def layer_for(layers, where: dict | None) -> str | None:
    """The layer at that path here, made with that colour when missing."""
    if not where:
        return None
    from .layers import PATH_SEPARATOR
    found = layers.find_by_path(where["path"])
    if found is not None:
        return found.id
    names = [n for n in where["path"].split(PATH_SEPARATOR) if n]
    parent = None
    for depth, name in enumerate(names):
        here = layers.find_by_path(PATH_SEPARATOR.join(names[:depth + 1]))
        if here is None:
            last = depth == len(names) - 1
            color = tuple(where["color"]) if last and where.get("color") else None
            here = layers.create(name, color, parent=parent)
        parent = here.id
    return parent
