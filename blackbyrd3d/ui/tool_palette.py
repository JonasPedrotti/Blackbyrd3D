"""The left tool strip: full-size tools, in as many columns as the height
needs.

A QToolBar with more buttons than its height allows quietly moves the
overflow into an extension chevron, which took Trim through Delete off
the palette on any window shorter than about 1120 px. Eight tools, Delete
among them, gone because the window was not tall enough.

The tools keep their size: smaller icons are harder to read. In a window
tall enough they stand in one column; in a shorter one they carry on in a
second column beside it, and a third if need be, rather than scrolling out
of sight. A column breaks between groups: a group that will not fit below
the last moves whole to the next column, and no column starts on a group
break.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QToolButton, QWidget

from .icons import command_icon

BUTTON = 30            # a square tool button
GAP = 2
PITCH = BUTTON + GAP   # one tool's worth of column
ICON = BUTTON - 8
RULE = 8               # the gap a group break leaves behind
MARGIN = 3
TOP_GAP = PITCH        # how far below the top the tools start


class ToolPalette(QWidget):
    """Every tool button, stacked in one column at one size."""

    def __init__(self, groups, invoke, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        # An empty column's worth, so that the size hint is answerable from
        # the moment the widget exists: reflow only works out the real
        # height once every button has been parented on, and a hint asked
        # for before then came back as an AttributeError from inside a Qt
        # override, which surfaces as a bare SystemError somewhere else.
        self._height = MARGIN * 2
        self._lead = 0
        self._room = None          # the height there is, None: unlimited
        self._columns = 1
        self._buttons: list[QToolButton] = []
        self._rules: list[QFrame] = []
        self._items: list[tuple[QWidget, bool]] = []   # (widget, is_rule)
        # (the rule above it or None, its buttons): a column breaks
        # between groups, never inside one that fits
        self._groups: list[tuple[QFrame | None, list[QToolButton]]] = []
        for index, group in enumerate(groups):
            rule = None
            if index:
                rule = QFrame(self)
                rule.setFrameShape(QFrame.Shape.HLine)
                rule.setFrameShadow(QFrame.Shadow.Plain)
                self._rules.append(rule)
                self._items.append((rule, True))
            members = []
            for label, command, *alt in group:
                button = self._button(label, command, invoke, *alt)
                self._buttons.append(button)
                self._items.append((button, False))
                members.append(button)
            self._groups.append((rule, members))
        self.reflow()

    def _button(self, label, command, invoke, alt=None) -> QToolButton:
        button = QToolButton(self)
        button.setText(label)
        icon = command_icon(command)
        if icon is not None:
            button.setIcon(icon)
            button.setIconSize(QSize(ICON, ICON))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setFixedSize(BUTTON, BUTTON)
        button.setAutoRaise(True)
        tip = f"{label}  ({command})"
        if alt is not None:
            # A right-click runs the alternative instead of a context menu.
            alt_label, alt_command = alt
            tip = _two_click_tip(tip, alt_label)
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda _pos, c=alt_command: invoke(c))
        button.setToolTip(tip)
        button.clicked.connect(lambda _=False, c=command: invoke(c))
        return button

    def columns(self) -> int:
        """How many columns the tools take at the height there is."""
        return self._columns

    def rules(self) -> list[QFrame]:
        return list(self._rules)

    def set_lead(self, lead: int) -> None:
        """Start the column this far down."""
        if lead != self._lead:
            self._lead = lead
            self.reflow()

    def set_room(self, height: int | None) -> None:
        """The height the tools have; past it they start another column."""
        if height != self._room:
            self._room = height
            self.reflow()

    def content_height(self) -> int:
        return self._height

    def natural_height(self) -> int:
        """The height of every tool in the one column."""
        rules = len(self._rules)
        tools = len(self._items) - rules
        return MARGIN + tools * PITCH + rules * RULE - GAP + MARGIN

    def reflow(self) -> None:
        """Lay the tools out, in order, at the size they are: down one
        column while there is room, then on in the next. A group that will
        not fit below the last goes whole to the next column; only one too
        tall for any column is split."""
        lead = self._lead
        room = self._room
        x, y, column = MARGIN, MARGIN, 0
        tallest = 0

        def fits(extra):
            return room is None or lead + y + extra - GAP + MARGIN <= room

        def next_column():
            nonlocal x, y, column, tallest
            tallest = max(tallest, y - GAP + MARGIN)
            column += 1
            x, y = MARGIN + column * PITCH, MARGIN

        for rule, members in self._groups:
            if rule is not None:
                rule.hide()
            whole = len(members) * PITCH
            if y > MARGIN and not fits(RULE + whole):
                next_column()                # the group goes whole
            if rule is not None and y > MARGIN:
                rule.setGeometry(x, lead + y + RULE // 2, BUTTON, 1)
                rule.show()
                y += RULE
            for button in members:
                # a group taller than a whole column has to give somewhere
                if y > MARGIN and not fits(PITCH):
                    next_column()
                button.move(x, lead + y)
                y += PITCH
        tallest = max(tallest, y - GAP + MARGIN)
        changed = column + 1 != self._columns
        self._columns = column + 1
        self._height = tallest
        if changed:
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        width = self._columns * PITCH - GAP + MARGIN * 2
        return QSize(width, self._height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


class _Strip(QScrollArea):
    """The palette's frame, as wide as its columns and as tall as the bar.

    Left alone a scroll area asks for a stock twelve columns by twenty-four
    lines whatever it holds, which as a toolbar widget is 68 px of empty
    strip beside a column of tools half that wide, and 432 px of height in
    a bar more than twice as tall.
    """

    def sizeHint(self) -> QSize:
        hint = self.widget().sizeHint()
        return QSize(hint.width(), hint.height())

    def minimumSizeHint(self) -> QSize:
        return QSize(self.sizeHint().width(), 0)

    def place_tools(self) -> None:
        """Columns for the height there is, and the tools a little below
        the top when one column has room to spare."""
        palette = self.widget()
        room = self.viewport().height()
        spare = room - palette.natural_height()
        palette.set_lead(max(0, min(TOP_GAP, spare)))
        columns = palette.columns()
        palette.set_room(room)
        if palette.columns() != columns:
            # one column more or less: the bar beside it has to make room
            self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place_tools()


def wyrm_button(invoke, parent=None) -> QWidget:
    """Wyrm's logo, at the foot of the strip, sized like every tool."""
    host = QWidget(parent)
    host.setObjectName("wyrmButton")
    host.setFixedSize(BUTTON + MARGIN * 2, BUTTON + MARGIN * 2)
    button = QToolButton(host)
    button.setIcon(command_icon("wyrm"))
    button.setIconSize(QSize(ICON + 2, ICON + 2))
    button.setFixedSize(BUTTON, BUTTON)
    button.move(MARGIN, MARGIN)
    button.setAutoRaise(True)
    button.setToolTip("Wyrm  (wyrm)")
    button.clicked.connect(lambda _=False: invoke())
    return host


def tool_strip(groups, invoke, parent=None) -> QScrollArea:
    """The palette, in as many columns as the height needs. With room to
    spare the tools start TOP_GAP below the top of the strip."""
    area = _Strip(parent)
    area.setObjectName("toolStrip")
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(ToolPalette(groups, invoke))
    area.setWidgetResizable(True)
    # Expanding, or the toolbar hands the strip its height hint and the
    # tools scroll in a window with room to spare.
    area.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    return area


def _two_click_tip(left: str, right: str) -> str:
    """One line per mouse button, each led by a picture of its click."""
    from html import escape
    from .icons import mouse_button_img
    rows = "".join(
        f"<tr><td>{mouse_button_img(side)}</td>"
        f'<td style="padding-left: 6px">{escape(text)}</td></tr>'
        for side, text in (("left", left), ("right", right)))
    return f'<table cellspacing="0" cellpadding="1">{rows}</table>'
