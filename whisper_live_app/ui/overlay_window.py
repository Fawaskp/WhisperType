import ctypes
import ctypes.wintypes as wintypes
import math

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QMenu, QApplication

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32

# Geometry (same as before)
COMPACT_SIZE = 80
EXPANDED_W = 200
PREVIEW_W = 320
ROW_H = 80

# State colors
COLORS = {
    "loading":      {"bg": "#3A3A3A", "fg": "#AAAAAA", "ring": "#666666"},
    "idle":         {"bg": "#1E1E2E", "fg": "#FFFFFF", "ring": "#5B9BD5"},
    "recording":    {"bg": "#B22D2D", "fg": "#FFFFFF", "ring": "#FF4444"},
    "transcribing": {"bg": "#C49000", "fg": "#FFFFFF", "ring": "#FFD700"},
    "error":        {"bg": "#1E1E2E", "fg": "#FFFFFF", "ring": "#E67E22"},
    "too_short":    {"bg": "#1E1E2E", "fg": "#FFFFFF", "ring": "#E67E22"},
    "preview":      {"bg": "#1E1E2E", "fg": "#FFFFFF", "ring": "#2ECC71"},
}


class OverlayWindow(QWidget):
    _state_signal = Signal(str, str)

    def __init__(self, root, on_click=None, on_stop=None, on_cancel=None,
                 initial_pos=None, on_drag_end=None):
        super().__init__()
        self.on_click = on_click
        self.on_stop = on_stop
        self.on_cancel = on_cancel
        self.on_drag_end = on_drag_end
        self._state = "loading"
        self._preview_text = ""

        # Animation state
        self._pulse_phase = 0
        self._spin_angle = 0
        self._loading_angle = 0
        self._wave_phase = 0.0

        # Drag state
        self._drag_start = None
        self._drag_moved = False

        # Button hit areas (display coords: cx, cy, r)
        self._btn_check = None
        self._btn_cancel = None

        self._cur_w = COMPACT_SIZE
        self._cur_h = ROW_H

        # Preview font
        self._preview_font = QFont("Segoe UI")
        self._preview_font.setPixelSize(11)

        # Window flags
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.95)

        # Position
        screen = QApplication.primaryScreen().geometry()
        if initial_pos and initial_pos[0] is not None:
            x, y = initial_pos
            x = max(0, min(int(x), screen.width() - COMPACT_SIZE))
            y = max(0, min(int(y), screen.height() - COMPACT_SIZE))
        else:
            x = screen.width() - COMPACT_SIZE - 20
            y = screen.height() // 2 - COMPACT_SIZE // 2

        self.setGeometry(x, y, COMPACT_SIZE, ROW_H)
        self.setFixedSize(COMPACT_SIZE, ROW_H)

        # Animation timer (50 ms interval, same as original)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(50)
        self._anim_timer.timeout.connect(self._animate_tick)

        # Auto-return timer (single-shot)
        self._auto_return_timer = QTimer(self)
        self._auto_return_timer.setSingleShot(True)
        self._auto_return_timer.timeout.connect(self._auto_return_idle)

        # Thread-safe state signal
        self._state_signal.connect(self._set_state_impl)

        self.show()
        self._apply_noactivate()

    # ── Win32 ─────────────────────────────────────────────────────────

    def _apply_noactivate(self):
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        style = style & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    # ── Resize ────────────────────────────────────────────────────────

    def _resize(self, w, h):
        if w == self._cur_w and h == self._cur_h:
            return
        self._cur_w = w
        self._cur_h = h
        self.setFixedSize(w, h)

    # ── State ─────────────────────────────────────────────────────────

    def set_state(self, state, text=""):
        """Thread-safe — can be called from any thread."""
        self._state_signal.emit(state, text)

    def _set_state_impl(self, state, text):
        self._state = state
        self._preview_text = text

        self._anim_timer.stop()
        self._auto_return_timer.stop()

        if state == "recording":
            self._resize(EXPANDED_W, ROW_H)
        elif state == "preview":
            self._resize(PREVIEW_W, ROW_H)
        else:
            self._resize(COMPACT_SIZE, ROW_H)

        if state in ("loading", "recording", "transcribing"):
            if state == "loading":
                self._loading_angle = 0
            elif state == "recording":
                self._pulse_phase = 0
                self._wave_phase = 0.0
            else:
                self._spin_angle = 0
            self._anim_timer.start()
        elif state == "error":
            self._auto_return_timer.start(1200)
        elif state == "too_short":
            self._auto_return_timer.start(800)
        elif state == "preview":
            self._auto_return_timer.start(2000)

        self.update()

    def _auto_return_idle(self):
        self.set_state("idle")

    # ── Animation ─────────────────────────────────────────────────────

    def _animate_tick(self):
        if self._state == "loading":
            self._loading_angle = (self._loading_angle + 8) % 360
        elif self._state == "recording":
            self._pulse_phase = (self._pulse_phase + 1) % 20
            self._wave_phase += 0.3
        elif self._state == "transcribing":
            self._spin_angle = (self._spin_angle + 15) % 360
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        colors = COLORS.get(self._state, COLORS["idle"])

        if self._state == "recording":
            self._draw_recording_expanded(p, colors)
        elif self._state == "preview":
            self._draw_preview(p, colors)
        else:
            self._draw_compact(p, colors)

        p.end()

    # ── Compact circle ────────────────────────────────────────────────

    def _draw_compact(self, p, colors):
        cx = cy = COMPACT_SIZE / 2   # 40
        r = COMPACT_SIZE / 2 - 3     # 37

        # Outer ring
        p.setPen(QPen(QColor(colors["ring"]), 3.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Inner filled circle
        ir = r - 5   # 32
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colors["bg"]))
        p.drawEllipse(QPointF(cx, cy), ir, ir)

        if self._state == "loading":
            self._draw_loading_dots(p, cx, cy, colors["fg"])
        elif self._state == "idle":
            self._draw_mic_icon(p, cx, cy, colors["fg"])
        elif self._state == "transcribing":
            self._draw_spinner_arcs(p, cx, cy, colors["fg"])
        elif self._state == "error":
            self._draw_error_icon(p, cx, cy)
        elif self._state == "too_short":
            self._draw_clock_icon(p, cx, cy)

    # ── Recording expanded ────────────────────────────────────────────

    def _draw_recording_expanded(self, p, colors):
        cx_left = ROW_H / 2   # 40
        cy = ROW_H / 2         # 40
        r = ROW_H / 2 - 3     # 37

        # Pulsing ring
        pulse = 0.6 + 0.4 * abs(math.sin(self._pulse_phase * math.pi / 10))
        bright = int(100 + 155 * pulse)
        pulse_ring = QColor(bright, 0x33, 0x33)

        p.setPen(QPen(pulse_ring, 3.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx_left, cy), r, r)

        ir = r - 5
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colors["bg"]))
        p.drawEllipse(QPointF(cx_left, cy), ir, ir)

        # Waveform bars (rounded pills)
        fg = QColor(colors["fg"])
        bar_w = 5
        gap = 4
        total = 3 * bar_w + 2 * gap
        x_start = cx_left - total / 2

        p.setBrush(fg)
        for i in range(3):
            phase_offset = i * 0.7
            bar_h = 10 + 14 * abs(math.sin(self._wave_phase + phase_offset))
            bx = x_start + i * (bar_w + gap)
            rr = bar_w / 2
            p.drawRoundedRect(QRectF(bx, cy - bar_h / 2, bar_w, bar_h), rr, rr)

        # ── Checkmark button ──
        btn_r = 18
        cx_chk = cx_left + r + 12 + btn_r

        p.setPen(QPen(QColor("#2ECC71"), 2))
        p.setBrush(QColor("#27AE60"))
        p.drawEllipse(QPointF(cx_chk, cy), btn_r, btn_r)

        pen = QPen(QColor("white"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline([
            QPointF(cx_chk - 7, cy + 1),
            QPointF(cx_chk - 2, cy + 7),
            QPointF(cx_chk + 8, cy - 6),
        ])
        self._btn_check = (cx_chk, cy, btn_r)

        # ── Cancel button ──
        cx_can = cx_chk + btn_r + 8 + btn_r

        p.setPen(QPen(QColor("#E74C3C"), 2))
        p.setBrush(QColor("#C0392B"))
        p.drawEllipse(QPointF(cx_can, cy), btn_r, btn_r)

        xs = 6
        pen = QPen(QColor("white"), 3, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(cx_can - xs, cy - xs), QPointF(cx_can + xs, cy + xs))
        p.drawLine(QPointF(cx_can + xs, cy - xs), QPointF(cx_can - xs, cy + xs))
        self._btn_cancel = (cx_can, cy, btn_r)

    # ── Preview ───────────────────────────────────────────────────────

    def _draw_preview(self, p, colors):
        cy = ROW_H / 2
        ccx = ROW_H / 2
        r = ROW_H / 2 - 3

        # Green circle with checkmark
        p.setPen(QPen(QColor("#2ECC71"), 3.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(ccx, cy), r, r)

        ir = r - 5
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#27AE60"))
        p.drawEllipse(QPointF(ccx, cy), ir, ir)

        pen = QPen(QColor("white"), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline([
            QPointF(ccx - 10, cy + 1),
            QPointF(ccx - 3, cy + 9),
            QPointF(ccx + 11, cy - 8),
        ])

        # Text bubble
        bx = ROW_H + 6
        bx_end = PREVIEW_W - 6
        by = 10
        by_end = ROW_H - 10
        br = 12

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#333344"))
        p.drawRoundedRect(QRectF(bx, by, bx_end - bx, by_end - by), br, br)

        display = self._preview_text
        if len(display) > 45:
            display = display[:42] + "..."

        p.setPen(QColor("#EEEEEE"))
        p.setFont(self._preview_font)
        p.drawText(QRectF(bx, by, bx_end - bx, by_end - by),
                   Qt.AlignCenter, display)

    # ── Icons ─────────────────────────────────────────────────────────

    def _draw_mic_icon(self, p, cx, cy, color):
        c = QColor(color)

        # Capsule body
        bw, bh = 8, 13
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(cx - bw, cy - bh, bw * 2, bh + 3), bw, bw)

        # Cradle arc (bottom half)
        p.setPen(QPen(c, 2.5))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - 15, cy - 12, 30, 26), 0, -180 * 16)

        # Stand
        pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(cx, cy + 14), QPointF(cx, cy + 21))
        p.drawLine(QPointF(cx - 9, cy + 21), QPointF(cx + 9, cy + 21))

    def _draw_loading_dots(self, p, cx, cy, color):
        c = QColor(color)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        r_orbit = 13
        dot_r = 4
        for i in range(3):
            angle = math.radians(self._loading_angle + i * 120)
            dx = cx + r_orbit * math.cos(angle)
            dy = cy + r_orbit * math.sin(angle)
            p.drawEllipse(QPointF(dx, dy), dot_r, dot_r)

    def _draw_spinner_arcs(self, p, cx, cy, color):
        c = QColor(color)

        # Outer arc
        r = 14
        p.setPen(QPen(c, 3.5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r),
                  int((self._spin_angle + 90) * 16), int(90 * 16))

        # Inner arc (opposite direction)
        sr = 8
        p.setPen(QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - sr, cy - sr, 2 * sr, 2 * sr),
                  int((-self._spin_angle + 60) * 16), int(60 * 16))

    def _draw_error_icon(self, p, cx, cy):
        r = 16
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E67E22"))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Exclamation stem
        p.setPen(QPen(QColor("white"), 3.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy - 10), QPointF(cx, cy + 3))

        # Dot
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(cx, cy + 8), 3, 3)

    def _draw_clock_icon(self, p, cx, cy):
        r = 16
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E67E22"))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Face outline
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 11, 11)

        # Hands
        pen = QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy - 8))
        p.drawLine(QPointF(cx, cy), QPointF(cx + 6, cy + 3))

        # Center dot
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(cx, cy), 2, 2)

    # ── Mouse events ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._drag_moved = False

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        current = event.globalPosition().toPoint()
        delta = current - self._drag_start
        if not self._drag_moved:
            if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                self._drag_moved = True
        if self._drag_moved:
            new_x = self.x() + delta.x()
            new_y = self.y() + delta.y()
            screen = QApplication.primaryScreen().geometry()
            new_x = max(0, min(new_x, screen.width() - self._cur_w))
            new_y = max(0, min(new_y, screen.height() - self._cur_h))
            self.move(new_x, new_y)
            self._drag_start = current

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if self._drag_moved:
            if self.on_drag_end:
                self.on_drag_end(self.x(), self.y())
            self._drag_start = None
            return

        if self._state == "recording":
            click_x = event.position().x()
            click_y = event.position().y()
            if self._btn_check and self._hit_test(click_x, click_y, *self._btn_check):
                if self.on_stop:
                    self.on_stop()
                self._drag_start = None
                return
            if self._btn_cancel and self._hit_test(click_x, click_y, *self._btn_cancel):
                if self.on_cancel:
                    self.on_cancel()
                self._drag_start = None
                return

        if self.on_click:
            self.on_click()
        self._drag_start = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        exit_action = menu.addAction("Exit")
        action = menu.exec(event.globalPos())
        if action == exit_action:
            QApplication.instance().quit()

    def _hit_test(self, x, y, cx, cy, r):
        return (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
