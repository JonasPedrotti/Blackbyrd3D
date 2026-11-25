"""File commands: save, open, import, export, new.

Each opens the window's file chooser by default and keeps its typed path
request when run with ``--headless`` or through the API.
"""

import os

from .. import fileio
from .base import FileReq, OptionReq, SelectReq, command, has_text_editor


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path.strip()))


def _thumbnail(ctx) -> bytes | None:
    """The active view as it is when saved, embedded in the .byrd as its
    preview, as Rhino keeps one in a .3dm: the welcome screen shows it."""
    vp = ctx.viewport
    if vp is None or not vp.isVisible():
        return None
    try:
        from PySide6.QtCore import QBuffer, Qt
        img = vp.grabFramebuffer().scaled(
            512, 512, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        return bytes(buf.data())
    except Exception:                                  # noqa: BLE001
        return None


@command("save", mutates=False)
def cmd_save(ctx):
    """Save the model as .byrd, or to another format by its extension (e.g.
    .3dm)."""
    default = getattr(ctx, "current_path", None) or "~/untitled.byrd"
    path = yield FileReq("Save as (.byrd or .3dm path)", default=default,
                         save=True, title="Save model",
                         filters=fileio.export_filter())
    path = _expand(path)
    # Only a name with no writable extension gets the native one: typed
    # "out.3dm" used to become out.3dm.byrd, so saving to Rhino needed
    # the menus (#5).
    if os.path.splitext(path)[1].lower() not in fileio.EXPORT_EXTS:
        path += ".byrd"
    window = ctx.window
    live = window is not None and not getattr(
        getattr(window, "processor", None), "headless", True)
    try:
        if live:
            window._export_showing_progress(path, thumbnail=_thumbnail(ctx))
        else:
            fileio.export_file(ctx.scene, path, thumbnail=_thumbnail(ctx))
    except fileio.Cancelled:
        ctx.echo("Save cancelled.")
        return
    ctx.current_path = path
    if ctx.window is not None:
        ctx.window.mark_saved()
    ctx.echo(f"Saved {len(ctx.scene.all())} object(s) to {path}")


@command("open", mutates=True)
def cmd_open(ctx):
    """Open a model, replacing the current one."""
    path = yield FileReq("File to open (.byrd)", title="Open model",
                         filters=fileio.import_filter())
    path = _expand(path)
    if not os.path.exists(path):
        ctx.echo(f"File not found: {path}")
        return
    notes = []
    fileio.import_file(ctx.scene, path, replace=True, notes=notes)
    ctx.current_path = path if path.endswith(".byrd") else None
    ctx.echo(f"Opened {path}: {len(ctx.scene.all())} object(s)"
             + "".join(f", {note}" for note in notes) + ".")
    if ctx.viewport:
        ctx.viewport.zoom_extents()


@command("import", aliases=("imp",), mutates=True, space="any")
def cmd_import(ctx):
    """Import a model file into the current one, or place an image as a
    picture."""
    path = yield FileReq("File to import (model or image)", title="Import",
                         filters=fileio.import_filter(pictures=True))
    path = _expand(path)
    if os.path.splitext(path)[1].lower() in fileio.PICTURE_EXTS:
        from .view import place_picture
        yield from place_picture(ctx, path)
        return
    if not os.path.exists(path):
        ctx.echo(f"File not found: {path}")
        return
    notes = []
    n = fileio.import_file(ctx.scene, path, notes=notes)
    ctx.echo(f"Imported {n} object(s) from {os.path.basename(path)}"
             + "".join(f", {note}" for note in notes) + ".")
    # Fit the view for the person who asked; a script or an assistant
    # driving the command headless leaves the modeller's camera alone.
    if ctx.viewport and has_text_editor(ctx):
        ctx.viewport.zoom_extents()


@command("export", aliases=("exp",), mutates=False)
def cmd_export(ctx):
    """Export what is picked: picked before, it goes without asking."""
    objs = yield SelectReq("Select objects to export")
    ids = [o.id for o in objs]
    path = yield FileReq("Export path (.step/.stp/.obj/.byrd)",
                         default="~/untitled.step", save=True,
                         title="Export", filters=fileio.export_filter())
    path = _expand(path)
    window = ctx.window
    processor = getattr(window, "processor", None)
    live = window is not None and not getattr(processor, "headless", True)
    options = {"only_ids": ids}
    if live:
        if path.lower().endswith(".stl"):
            quality = window._pick_stl_quality()
            if quality is None:
                ctx.echo("Export cancelled.")
                return
            options["stl_quality"] = quality
        options["rhino_version"] = fileio.rhino_version_from_filter(
            getattr(window, "_picked_filter", ""))
    try:
        if live:
            note = window._export_showing_progress(path, **options)
        else:
            note = fileio.export_file(ctx.scene, path, **options)
    except fileio.Cancelled:
        ctx.echo("Export cancelled.")
        return
    ctx.echo(f"Exported {len(ids)} object(s) to {path}"
             + (f" ({note})" if note else ""))


@command("setdefaultapp", mutates=False)
def cmd_setdefaultapp(ctx):
    """Make Blackbyrd3D the default application for .byrd files."""
    from ..utils import file_assoc
    _, message = file_assoc.make_default()
    ctx.echo(message)
    yield from ()


@command("new", mutates=True)
def cmd_new(ctx):
    """Clear the scene and start a new document."""
    confirm = yield OptionReq("Clear the scene?", options=["Yes", "No"],
                              default="No")
    if confirm == "Yes":
        ctx.scene.clear()
        ctx.current_path = None
        ctx.echo("New document.")
    else:
        ctx.echo("Cancelled.")
