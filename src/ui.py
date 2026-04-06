from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegion,
    QTransform,
)
from PySide6.QtWidgets import QApplication, QWidget

from .animations import AnimationClock, choose_animation
from .assets import AssetCatalog
from .constants import (
    APP_NAME,
    BUTTON_CENTERS,
    DEFAULT_WINDOW_SCALE,
    DEVICE_BODY_RECT,
    DEVICE_BOUNDS,
    DEVICE_LOOP_INNER,
    DEVICE_LOOP_OUTER,
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
        self.show_status_until = now_local()
        self.pressed_button = ""
        self._drag_offset: QPoint | None = None

        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        bounds = QRectF(*DEVICE_BOUNDS)
        self.resize(int(bounds.width() * DEFAULT_WINDOW_SCALE), int(bounds.height() * DEFAULT_WINDOW_SCALE))
        self.setMinimumSize(int(bounds.width() * 0.48), int(bounds.height() * 0.48))

        self._install_timers()
        self._install_shortcuts()
        self.game.tick(now_local())
        self._apply_window_shape()

    def _install_timers(self) -> None:
        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self._on_logic_tick)
        self.logic_timer.start(1000)

        self.paint_timer = QTimer(self)
        self.paint_timer.timeout.connect(self.update)
        self.paint_timer.start(120)

    def _install_shortcuts(self) -> None:
        for shortcut in ("Ctrl+Q", "Ctrl+W"):
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(self.close)
            self.addAction(action)

    def _on_logic_tick(self) -> None:
        if self.game.tick(now_local()):
            self._save()
        self.update()

    def _save(self) -> None:
        self.store.save(self.game.serialize())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save()
        return super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._apply_window_shape()
        return super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        button = key_to_button(event.key())
        if button:
            self._handle_button(button)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_point = self._widget_to_scene(event.position())
            button = button_at_point(scene_point)
            if button:
                self._handle_button(button)
                event.accept()
                return

            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _handle_button(self, button: str) -> None:
        now = now_local()
        self.pressed_button = button
        QTimer.singleShot(140, self._clear_pressed_button)

        if not self.game.state.alive and button == "B":
            self.game.perform("RESET", now)
            self.menu_index = 0
            self.show_status_until = now - timedelta(seconds=1)
            self._save()
            self.update()
            return

        if button == "A":
            self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
        elif button == "B":
            action = MENU_ITEMS[self.menu_index]
            if action == "STATUS":
                self.show_status_until = now + timedelta(seconds=6)
            self.game.perform(action, now)
            self._save()
        elif button == "C":
            self.show_status_until = now - timedelta(seconds=1)
            self.game.state.message = ""
            self.game.state.message_until = ""
            self.update()
            return

        self.update()

    def _clear_pressed_button(self) -> None:
        self.pressed_button = ""
        self.update()

    def _bounds(self) -> QRectF:
        return QRectF(*DEVICE_BOUNDS)

    def _scale(self) -> float:
        bounds = self._bounds()
        return min(self.width() / bounds.width(), self.height() / bounds.height())

    def _origin(self) -> QPointF:
        bounds = self._bounds()
        scale = self._scale()
        width = bounds.width() * scale
        height = bounds.height() * scale
        return QPointF((self.width() - width) / 2, (self.height() - height) / 2)

    def _map_rect(self, scene_rect: QRectF) -> QRectF:
        bounds = self._bounds()
        scale = self._scale()
        origin = self._origin()
        return QRectF(
            origin.x() + ((scene_rect.left() - bounds.left()) * scale),
            origin.y() + ((scene_rect.top() - bounds.top()) * scale),
            scene_rect.width() * scale,
            scene_rect.height() * scale,
        )

    def _map_point(self, scene_point: QPointF) -> QPointF:
        bounds = self._bounds()
        scale = self._scale()
        origin = self._origin()
        return QPointF(
            origin.x() + ((scene_point.x() - bounds.left()) * scale),
            origin.y() + ((scene_point.y() - bounds.top()) * scale),
        )

    def _widget_to_scene(self, point: QPointF) -> QPointF:
        bounds = self._bounds()
        scale = self._scale()
        origin = self._origin()
        return QPointF(
            bounds.left() + ((point.x() - origin.x()) / scale),
            bounds.top() + ((point.y() - origin.y()) / scale),
        )

    def _device_path_scene(self) -> QPainterPath:
        body = QPainterPath()
        body.addEllipse(QRectF(*DEVICE_BODY_RECT))

        loop = QPainterPath()
        loop.addEllipse(QRectF(*DEVICE_LOOP_OUTER))

        hole = QPainterPath()
        hole.addEllipse(QRectF(*DEVICE_LOOP_INNER))

        return body.united(loop).subtracted(hole)

    def _device_path_widget(self) -> QPainterPath:
        scale = self._scale()
        origin = self._origin()
        bounds = self._bounds()

        transform = QTransform()
        transform.translate(origin.x(), origin.y())
        transform.scale(scale, scale)
        transform.translate(-bounds.left(), -bounds.top())
        return transform.map(self._device_path_scene())

    def _apply_window_shape(self) -> None:
        if QApplication.platformName() == "offscreen":
            self.clearMask()
            return
        path = self._device_path_widget()
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _font(self, pixel_size: float, bold: bool = True) -> QFont:
        font = QFont("DejaVu Sans Mono")
        font.setBold(bold)
        font.setPixelSize(max(8, int(round(pixel_size * self._scale()))))
        font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        return font

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        device_rect = self._map_rect(QRectF(*DEVICE_BOUNDS))
        painter.save()
        painter.setClipPath(self._device_path_widget())
        painter.drawPixmap(device_rect, self.assets.casing, QRectF(*DEVICE_BOUNDS))
        self._paint_lcd(painter)
        self._paint_button_feedback(painter)
        painter.restore()

    def _paint_lcd(self, painter: QPainter) -> None:
        screen_rect = self._map_rect(QRectF(*LCD_RECT))
        content_scene = QRectF(
            LCD_RECT[0] + LCD_INSET,
            LCD_RECT[1] + LCD_INSET,
            LCD_RECT[2] - (LCD_INSET * 2),
            LCD_RECT[3] - (LCD_INSET * 2),
        )
        content_rect = self._map_rect(content_scene)

        screen_path = QPainterPath()
        radius = LCD_RADIUS * self._scale()
        screen_path.addRoundedRect(screen_rect, radius, radius)

        painter.save()
        painter.setClipPath(screen_path)
        painter.fillPath(screen_path, QColor(*LCD_BACKGROUND))
        self._paint_lcd_lines(painter, screen_rect)
        self._paint_header(painter, content_rect)
        self._paint_sprite(painter, content_rect)

        if self.show_status_until > now_local():
            self._paint_status_panel(painter, content_rect)

        self._paint_footer(painter, content_rect)
        painter.restore()

        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(92, 86, 66, 72), max(1, int(round(2 * self._scale())))))
        painter.drawPath(screen_path)
        painter.restore()

    def _paint_lcd_lines(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QPen(QColor(*LCD_LINE), max(1, int(round(self._scale())))))
        step = max(3, int(round(4 * self._scale())))
        y = int(rect.top()) + step
        while y < int(rect.bottom()):
            painter.drawLine(int(rect.left()) + 5, y, int(rect.right()) - 5, y)
            y += step
        painter.restore()

    def _paint_header(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(QColor(*LCD_TEXT))
        painter.setFont(self._font(24))
        painter.drawText(
            QRectF(rect.left(), rect.top() + (4 * self._scale()), rect.width(), 30 * self._scale()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "SAKUNA",
        )

        painter.setFont(self._font(22))
        line = "GAME OVER" if not self.game.state.alive else f"LEVEL {self.game.state.level:02d}"
        if self.game.state.stage == "egg" and self.game.state.alive:
            line = "EGG"
        painter.drawText(
            QRectF(rect.left(), rect.top() + (34 * self._scale()), rect.width(), 28 * self._scale()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            line,
        )
        painter.restore()

    def _paint_sprite(self, painter: QPainter, rect: QRectF) -> None:
        decision = choose_animation(self.game.state, self.game.state.transient_animation or None)
        frames = self.assets.frames(decision.name)
        frame_index = self.animation_clock.frame_index(
            decision.name,
            len(frames),
            decision.interval_ms,
            decision.loop,
        )
        sprite = frames[frame_index]

        target_area = QRectF(
            rect.left() + (18 * self._scale()),
            rect.top() + (82 * self._scale()),
            rect.width() - (36 * self._scale()),
            rect.height() - (156 * self._scale()),
        )
        scaled = self._scale_nearest(sprite, target_area)
        x = target_area.center().x() - (scaled.width() / 2)
        y = target_area.bottom() - scaled.height()
        painter.drawPixmap(int(round(x)), int(round(y)), scaled)

        if self.game.state.poop_count > 1 and decision.name not in {"clean", "dead"}:
            self._paint_extra_poop(painter, target_area)

    def _paint_extra_poop(self, painter: QPainter, rect: QRectF) -> None:
        icon = self.assets.icons["poop"]
        base_scale = max(1, int(round(self._scale() * 2)))
        scaled = icon.scaled(
            icon.width() * base_scale,
            icon.height() * base_scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        for index in range(1, self.game.state.poop_count):
            px = rect.left() + (14 * self._scale()) + ((index - 1) * (scaled.width() + (6 * self._scale())))
            py = rect.bottom() - scaled.height() - (4 * self._scale())
            painter.drawPixmap(int(round(px)), int(round(py)), scaled)

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
        footer_rect = QRectF(
            rect.left() + (16 * self._scale()),
            rect.bottom() - (36 * self._scale()),
            rect.width() - (32 * self._scale()),
            28 * self._scale(),
        )

        if not self.game.state.alive:
            footer_text = "B NEW EGG"
        elif self.game.state.message:
            footer_text = self.game.state.message
        elif self.game.state.attention:
            footer_text = f"CALL {self.game.state.attention_reason}"
        else:
            footer_text = MENU_ITEMS[self.menu_index]

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(*LCD_MESSAGE))
        painter.drawRoundedRect(footer_rect, 10 * self._scale(), 10 * self._scale())
        painter.setPen(QColor(*LCD_TEXT))
        painter.setFont(self._font(18))
        painter.drawText(footer_rect, Qt.AlignmentFlag.AlignCenter, footer_text)
        painter.restore()

    def _paint_status_panel(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        panel_rect = QRectF(
            rect.left() + (12 * self._scale()),
            rect.top() + (90 * self._scale()),
            rect.width() - (24 * self._scale()),
            104 * self._scale(),
        )
        painter.setPen(QPen(QColor(*LCD_PANEL_BORDER), max(1, int(round(self._scale())))))
        painter.setBrush(QColor(*LCD_PANEL))
        painter.drawRoundedRect(panel_rect, 10 * self._scale(), 10 * self._scale())
        painter.setPen(QColor(*LCD_TEXT))
        painter.setFont(self._font(16))

        row_y = panel_rect.top() + (17 * self._scale())
        for row in self.game.status_rows():
            painter.drawText(
                QRectF(panel_rect.left() + (12 * self._scale()), row_y, panel_rect.width(), 18 * self._scale()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                row,
            )
            row_y += 21 * self._scale()
        painter.restore()

    def _paint_button_feedback(self, painter: QPainter) -> None:
        if not self.pressed_button:
            return

        center_scene = BUTTON_CENTERS[self.pressed_button]
        center = self._map_point(QPointF(*center_scene))
        radius = 28 * self._scale()

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(120, 64, 82, 46))
        painter.drawEllipse(center, radius, radius)
        painter.restore()
