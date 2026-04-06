from __future__ import annotations

from math import hypot

from PySide6.QtCore import QPointF, Qt

from .constants import BUTTON_CENTERS, BUTTON_RADIUS


KEY_BINDINGS = {
    Qt.Key.Key_Left: "A",
    Qt.Key.Key_Tab: "A",
    Qt.Key.Key_A: "A",
    Qt.Key.Key_Return: "B",
    Qt.Key.Key_Enter: "B",
    Qt.Key.Key_Space: "B",
    Qt.Key.Key_Backspace: "C",
    Qt.Key.Key_Escape: "C",
    Qt.Key.Key_C: "C",
}


def key_to_button(key: int) -> str | None:
    return KEY_BINDINGS.get(Qt.Key(key))


def button_at_point(point: QPointF) -> str | None:
    for button, (x, y) in BUTTON_CENTERS.items():
        distance = hypot(point.x() - x, point.y() - y)
        if distance <= BUTTON_RADIUS:
            return button
    return None
