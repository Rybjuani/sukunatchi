from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from .animations import AnimationClock, choose_animation
from .assets import AssetCatalog
from .constants import (
    APP_NAME,
    BASE_SIZE,
    BUTTON_CENTERS,
    LCD_BACKGROUND,
    LCD_INSET,
    LCD_LINE,
    LCD_MESSAGE,
    LCD_PANEL,
    LCD_PANEL_BORDER,
    LCD_RADIUS,
    LCD_RECT,
    LCD_TEXT,
    MENU_ITEMS,
)
from .controls import button_at_point, key_to_button
from .pet import PetGame, now_local
from .storage import SaveStore


class TamagotchiWindow(QWidget):
    def __init__(self, assets: AssetCatalog, game: PetGame, store: SaveStore) -> None:
        super().__init__()
        self.assets = assets
        self.game = game
        self.store = store
        self.animation_clock = AnimationClock()
        self.menu_index = 0
        self.menu_visible_until = now_local()
        self.show_status_until = now_local()
        self.pressed_button = ""
        self._last_saved_message = ""

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(BASE_SIZE, BASE_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._install_timers()
        self._install_shortcuts()
        self.game.tick(now_local())

    def _install_timers(self) -> None:
        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self._on_logic_tick)
        self.logic_timer.start(1000)

        self.paint_timer = QTimer(self)
        self.paint_timer.timeout.connect(self.update)
        self.paint_timer.start(120)

    def _install_shortcuts(self) -> None:
        close_action = QAction(self)
        close_action.setShortcut("Ctrl+Q")
        close_action.triggered.connect(self.close)
        self.addAction(close_action)

    def _on_logic_tick(self) -> None:
        if self.game.tick(now_local()):
            self._save()
        self.update()

    def _save(self) -> None:
        self.store.save(self.game.serialize())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save()
        return super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        button = key_to_button(event.key())
        if button:
            self._handle_button(button)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        button = button_at_point(QPointF(event.position()))
        if button:
            self._handle_button(button)
            event.accept()
            return
        super().mousePressEvent(event)

    def _handle_button(self, button: str) -> None:
        now = now_local()
        self.pressed_button = button
        QTimer.singleShot(140, self._clear_pressed_button)

        if not self.game.state.alive and button == "B":
            self.game.perform("RESET", now)
            self.menu_index = 0
            self._save()
            self.update()
            return

        if button == "A":
            self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
            self.menu_visible_until = now.replace(microsecond=0)
            self.menu_visible_until = self.menu_visible_until + self._seconds(5)
        elif button == "B":
            action = MENU_ITEMS[self.menu_index]
            if action == "STATUS":
                self.show_status_until = now + self._seconds(6)
                self.game.perform("STATUS", now)
            else:
                self.game.perform(action, now)
            self.menu_visible_until = now + self._seconds(4)
            self._save()
        elif button == "C":
            self.show_status_until = now - self._seconds(1)
            self.menu_visible_until = now - self._seconds(1)
            self.game.state.message = ""
            self.game.state.message_until = ""
            self._save()

        self.update()

    def _seconds(self, value: int):
        from datetime import timedelta

        return timedelta(seconds=value)

    def _clear_pressed_button(self) -> None:
        self.pressed_button = ""
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)

        painter.drawPixmap(self.rect(), self.assets.casing)
        self._paint_lcd(painter)
        self._paint_button_feedback(painter)

    def _paint_lcd(self, painter: QPainter) -> None:
        x, y, width, height = LCD_RECT
        screen_rect = QRectF(x, y, width, height)
        content_rect = screen_rect.adjusted(LCD_INSET, LCD_INSET, -LCD_INSET, -LCD_INSET)

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*LCD_BACKGROUND))
        painter.drawRoundedRect(content_rect, LCD_RADIUS, LCD_RADIUS)
        self._paint_lcd_lines(painter, content_rect)
        painter.restore()

        self._paint_header(painter, content_rect)
        self._paint_sprite(painter, content_rect)
        self._paint_footer(painter, content_rect)

        if self.show_status_until > now_local():
            self._paint_status_panel(painter, content_rect)

    def _paint_lcd_lines(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QPen(QColor(*LCD_LINE), 1))
        y = int(rect.top()) + 1
        while y < int(rect.bottom()):
            painter.drawLine(int(rect.left()) + 4, y, int(rect.right()) - 4, y)
            y += 4
        painter.restore()

    def _paint_header(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QColor(*LCD_TEXT))

        title_font = QFont("DejaVu Sans Mono", 16, QFont.Weight.Bold)
        title_font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        sub_font = QFont("DejaVu Sans Mono", 15, QFont.Weight.Bold)
        sub_font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)

        painter.setFont(title_font)
        painter.drawText(
            QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 28),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "SAKUNA",
        )

        painter.setFont(sub_font)
        line = "GAME OVER" if not self.game.state.alive else f"CE Level: {self.game.state.level:02d}"
        painter.drawText(
            QRectF(rect.left() + 12, rect.top() + 34, rect.width() - 24, 28),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            line,
        )
        painter.restore()

    def _paint_sprite(self, painter: QPainter, rect: QRectF) -> None:
        now = now_local()
        decision = choose_animation(self.game.state, self.game.state.transient_animation or None)
        frames = self.assets.frames(decision.name)
        frame_index = self.animation_clock.frame_index(
            decision.name,
            len(frames),
            decision.interval_ms,
            decision.loop,
        )
        sprite = frames[frame_index]

        target_area = QRectF(rect.left() + 26, rect.top() + 82, rect.width() - 52, rect.height() - 136)
        scaled = self._scale_nearest(sprite, target_area)
        x = target_area.center().x() - scaled.width() / 2
        y = target_area.bottom() - scaled.height()
        painter.drawPixmap(int(x), int(y), scaled)

        if self.game.state.poop_count > 1 and decision.name not in {"clean", "dead"}:
            self._paint_extra_poop(painter, target_area)

    def _paint_extra_poop(self, painter: QPainter, rect: QRectF) -> None:
        icon = self.assets.icons["poop"]
        size = icon.size()
        scaled = icon.scaled(size.width() * 2, size.height() * 2, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        for index in range(1, self.game.state.poop_count):
            px = rect.left() + 20 + ((index - 1) * (scaled.width() + 6))
            py = rect.bottom() - scaled.height() - 6
            painter.drawPixmap(int(px), int(py), scaled)

    def _scale_nearest(self, sprite: QPixmap, rect: QRectF) -> QPixmap:
        max_scale_x = max(1, int(rect.width() // max(1, sprite.width())))
        max_scale_y = max(1, int(rect.height() // max(1, sprite.height())))
        scale = max(1, min(max_scale_x, max_scale_y))
        return sprite.scaled(
            sprite.width() * scale,
            sprite.height() * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def _paint_footer(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QColor(*LCD_TEXT))
        font = QFont("DejaVu Sans Mono", 13, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        painter.setFont(font)

        footer_text = ""
        current = now_local()
        if not self.game.state.alive:
            footer_text = "B: NEW EGG"
        elif self.game.state.message:
            footer_text = self.game.state.message
        elif self.menu_visible_until > current:
            footer_text = f">{MENU_ITEMS[self.menu_index]}"
        elif self.game.state.attention:
            footer_text = f"CALL: {self.game.state.attention_reason}"

        if footer_text:
            footer_rect = QRectF(rect.left() + 44, rect.bottom() - 34, rect.width() - 88, 24)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(*LCD_MESSAGE))
            painter.drawRoundedRect(footer_rect, 10, 10)
            painter.setPen(QColor(*LCD_TEXT))
            painter.drawText(footer_rect, Qt.AlignmentFlag.AlignCenter, footer_text)
        painter.restore()

    def _paint_status_panel(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        panel_rect = QRectF(rect.left() + 24, rect.top() + 84, rect.width() - 48, 96)
        painter.setPen(QPen(QColor(*LCD_PANEL_BORDER), 1))
        painter.setBrush(QColor(*LCD_PANEL))
        painter.drawRoundedRect(panel_rect, 12, 12)
        painter.setPen(QColor(*LCD_TEXT))
        font = QFont("DejaVu Sans Mono", 12, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        painter.setFont(font)
        row_y = panel_rect.top() + 18
        for row in self.game.status_rows():
            painter.drawText(
                QRectF(panel_rect.left() + 12, row_y, panel_rect.width() - 24, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                row,
            )
            row_y += 20
        painter.restore()

    def _paint_button_feedback(self, painter: QPainter) -> None:
        if not self.pressed_button:
            return
        center = BUTTON_CENTERS[self.pressed_button]
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(120, 64, 82, 46))
        painter.drawEllipse(QPointF(*center), 42, 42)
        painter.restore()
