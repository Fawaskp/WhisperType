import ctypes
import ctypes.wintypes as wintypes
import tkinter as tk
import math
import numpy as np
from PIL import Image, ImageDraw, ImageTk, ImageFont

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32

# Supersampling — draw at 3x, downscale with LANCZOS for smooth edges
AA = 3

# Geometry (bigger than before for more clarity)
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


def _load_font(size):
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


_PREVIEW_FONT = _load_font(int(11 * AA))


class OverlayWindow:
    def __init__(self, root, on_click=None, on_stop=None, on_cancel=None,
                 initial_pos=None, on_drag_end=None):
        self.root = root
        self.on_click = on_click
        self.on_stop = on_stop
        self.on_cancel = on_cancel
        self.on_drag_end = on_drag_end
        self._state = "loading"
        self._preview_text = ""

        self._photo = None  # prevent GC of PhotoImage

        # Animation state
        self._pulse_phase = 0
        self._pulse_job = None
        self._spin_angle = 0
        self._spin_job = None
        self._loading_angle = 0
        self._loading_job = None
        self._wave_phase = 0
        self._auto_return_job = None

        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_moved = False

        # Button hit areas (1x display coords)
        self._btn_check = None
        self._btn_cancel = None

        self._initial_pos = initial_pos
        self._build_window()
        self._apply_noactivate()
        self._draw()

    def _build_window(self):
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.95)

        self.win.configure(bg="magenta")
        self.win.wm_attributes("-transparentcolor", "magenta")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        if self._initial_pos and self._initial_pos[0] is not None:
            x, y = self._initial_pos
            x = max(0, min(int(x), screen_w - COMPACT_SIZE))
            y = max(0, min(int(y), screen_h - COMPACT_SIZE))
        else:
            x = screen_w - COMPACT_SIZE - 20
            y = screen_h // 2 - COMPACT_SIZE // 2

        self._cur_w = COMPACT_SIZE
        self._cur_h = ROW_H
        self.win.geometry(f"{COMPACT_SIZE}x{ROW_H}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.win, width=COMPACT_SIZE, height=ROW_H,
            bg="magenta", highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="Exit", command=self._on_exit)

    def _apply_noactivate(self):
        self.win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        style = style & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _resize(self, w, h):
        if w == self._cur_w and h == self._cur_h:
            return
        self._cur_w = w
        self._cur_h = h
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.canvas.config(width=w, height=h)

    def set_state(self, state, text=""):
        self._state = state
        self._preview_text = text

        if self._auto_return_job:
            self.root.after_cancel(self._auto_return_job)
            self._auto_return_job = None
        if self._pulse_job:
            self.root.after_cancel(self._pulse_job)
            self._pulse_job = None
        if self._spin_job:
            self.root.after_cancel(self._spin_job)
            self._spin_job = None
        if self._loading_job:
            self.root.after_cancel(self._loading_job)
            self._loading_job = None

        if state == "recording":
            self._resize(EXPANDED_W, ROW_H)
        elif state == "preview":
            self._resize(PREVIEW_W, ROW_H)
        else:
            self._resize(COMPACT_SIZE, ROW_H)

        if state == "loading":
            self._loading_angle = 0
            self._animate_loading()
        elif state == "recording":
            self._pulse_phase = 0
            self._wave_phase = 0
            self._animate_pulse()
        elif state == "transcribing":
            self._spin_angle = 0
            self._animate_spin()
        elif state == "error":
            self._draw()
            self._auto_return_job = self.root.after(1200, self._auto_return_idle)
        elif state == "too_short":
            self._draw()
            self._auto_return_job = self.root.after(800, self._auto_return_idle)
        elif state == "preview":
            self._draw()
            self._auto_return_job = self.root.after(2000, self._auto_return_idle)
        else:
            self._draw()

    def _auto_return_idle(self):
        self._auto_return_job = None
        self.set_state("idle")

    # ── Render pipeline ──────────────────────────────────────────────

    def _new_frame(self):
        w, h = self._cur_w * AA, self._cur_h * AA
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    def _show_frame(self, img):
        w, h = self._cur_w, self._cur_h
        img = img.resize((w, h), Image.LANCZOS)
        arr = np.array(img)
        alpha = arr[:, :, 3]
        visible = alpha > 30
        result = np.full((h, w, 3), (255, 0, 255), dtype=np.uint8)
        result[visible] = arr[visible][:, :3]
        self._photo = ImageTk.PhotoImage(Image.fromarray(result, "RGB"))
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

    # ── Drawing ──────────────────────────────────────────────────────

    def _draw(self):
        self.canvas.delete("all")
        colors = COLORS.get(self._state, COLORS["idle"])
        img, d = self._new_frame()

        if self._state == "recording":
            self._draw_recording_expanded(d, colors)
        elif self._state == "preview":
            self._draw_preview(d, colors)
        else:
            self._draw_compact(d, colors)

        self._show_frame(img)

    # ── Compact circle ───────────────────────────────────────────────

    def _draw_compact(self, d, colors):
        S = AA
        sz = COMPACT_SIZE * S
        cx, cy = sz / 2, sz / 2
        r = sz / 2 - 3 * S

        # Outer ring
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=colors["ring"], width=int(3.5 * S))
        # Inner filled circle
        ir = r - 5 * S
        d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=colors["bg"])

        if self._state == "loading":
            self._draw_loading_dots(d, cx, cy, colors["fg"])
        elif self._state == "idle":
            self._draw_mic_icon(d, cx, cy, colors["fg"])
        elif self._state == "transcribing":
            self._draw_spinner_arcs(d, cx, cy, colors["fg"])
        elif self._state == "error":
            self._draw_error_icon(d, cx, cy)
        elif self._state == "too_short":
            self._draw_clock_icon(d, cx, cy)

    # ── Recording expanded ───────────────────────────────────────────

    def _draw_recording_expanded(self, d, colors):
        S = AA
        h = ROW_H * S
        cx_left = ROW_H * S / 2
        cy = h / 2
        r = ROW_H * S / 2 - 3 * S

        # Pulsing ring
        pulse = 0.6 + 0.4 * abs(math.sin(self._pulse_phase * math.pi / 10))
        bright = int(100 + 155 * pulse)
        pulse_ring = f"#{bright:02x}3333"

        d.ellipse([cx_left - r, cy - r, cx_left + r, cy + r],
                  outline=pulse_ring, width=int(3.5 * S))
        ir = r - 5 * S
        d.ellipse([cx_left - ir, cy - ir, cx_left + ir, cy + ir],
                  fill=colors["bg"])

        # Waveform bars (rounded pill shapes)
        bar_w = int(5 * S)
        gap = int(4 * S)
        total = 3 * bar_w + 2 * gap
        x_start = cx_left - total / 2
        for i in range(3):
            phase_offset = i * 0.7
            bar_h = (10 + 14 * abs(math.sin(self._wave_phase + phase_offset))) * S
            bx = x_start + i * (bar_w + gap)
            rr = bar_w // 2
            d.rounded_rectangle(
                [bx, cy - bar_h / 2, bx + bar_w, cy + bar_h / 2],
                radius=rr, fill=colors["fg"])

        # ── Checkmark button ──
        btn_r = int(18 * S)
        cx_chk = cx_left + r + int(12 * S) + btn_r
        d.ellipse([cx_chk - btn_r, cy - btn_r, cx_chk + btn_r, cy + btn_r],
                  fill="#27AE60", outline="#2ECC71", width=int(2 * S))
        # Checkmark lines with rounded caps
        pts = [(cx_chk - 7 * S, cy + 1 * S),
               (cx_chk - 2 * S, cy + 7 * S),
               (cx_chk + 8 * S, cy - 6 * S)]
        lw = int(3 * S)
        d.line(pts, fill="white", width=lw, joint="curve")
        cap = lw / 2
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - cap, p[1] - cap, p[0] + cap, p[1] + cap],
                      fill="white")
        self._btn_check = (cx_chk / S, cy / S, btn_r / S)

        # ── Cancel button ──
        cx_can = cx_chk + btn_r + int(8 * S) + btn_r
        d.ellipse([cx_can - btn_r, cy - btn_r, cx_can + btn_r, cy + btn_r],
                  fill="#C0392B", outline="#E74C3C", width=int(2 * S))
        xs = int(6 * S)
        lw2 = int(3 * S)
        d.line([(cx_can - xs, cy - xs), (cx_can + xs, cy + xs)],
               fill="white", width=lw2)
        d.line([(cx_can + xs, cy - xs), (cx_can - xs, cy + xs)],
               fill="white", width=lw2)
        cap2 = lw2 / 2
        for p in [(cx_can - xs, cy - xs), (cx_can + xs, cy + xs),
                  (cx_can + xs, cy - xs), (cx_can - xs, cy + xs)]:
            d.ellipse([p[0] - cap2, p[1] - cap2, p[0] + cap2, p[1] + cap2],
                      fill="white")
        self._btn_cancel = (cx_can / S, cy / S, btn_r / S)

    # ── Preview ──────────────────────────────────────────────────────

    def _draw_preview(self, d, colors):
        S = AA
        h = ROW_H * S
        cy = h / 2
        ccx = ROW_H * S / 2
        r = ROW_H * S / 2 - 3 * S

        # Green circle with checkmark
        d.ellipse([ccx - r, cy - r, ccx + r, cy + r],
                  outline="#2ECC71", width=int(3.5 * S))
        ir = r - 5 * S
        d.ellipse([ccx - ir, cy - ir, ccx + ir, cy + ir], fill="#27AE60")
        pts = [(ccx - 10 * S, cy + 1 * S),
               (ccx - 3 * S, cy + 9 * S),
               (ccx + 11 * S, cy - 8 * S)]
        lw = int(3.5 * S)
        d.line(pts, fill="white", width=lw, joint="curve")
        cap = lw / 2
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - cap, p[1] - cap, p[0] + cap, p[1] + cap],
                      fill="white")

        # Text bubble
        bx = (ROW_H + 6) * S
        bx_end = (PREVIEW_W - 6) * S
        by = int(10 * S)
        by_end = int((ROW_H - 10) * S)
        br = int(12 * S)
        d.rounded_rectangle([bx, by, bx_end, by_end],
                            radius=br, fill="#333344")

        display = self._preview_text
        if len(display) > 45:
            display = display[:42] + "..."
        tx = (bx + bx_end) / 2
        d.text((tx, cy), display, fill="#EEEEEE",
               font=_PREVIEW_FONT, anchor="mm")

    # ── Icons ────────────────────────────────────────────────────────

    def _draw_mic_icon(self, d, cx, cy, color):
        S = AA
        bw, bh = int(8 * S), int(13 * S)

        # Capsule body
        d.rounded_rectangle(
            [cx - bw, cy - bh, cx + bw, cy + int(3 * S)],
            radius=bw, fill=color)

        # Cradle arc (bottom half)
        d.arc([cx - 15 * S, cy - 12 * S, cx + 15 * S, cy + 14 * S],
              start=0, end=180, fill=color, width=int(2.5 * S))

        # Stand
        lw = int(2.5 * S)
        d.line([(cx, cy + 14 * S), (cx, cy + 21 * S)], fill=color, width=lw)
        d.line([(cx - 9 * S, cy + 21 * S), (cx + 9 * S, cy + 21 * S)],
               fill=color, width=lw)
        # Rounded caps on base
        cap = lw / 2
        d.ellipse([cx - 9 * S - cap, cy + 21 * S - cap,
                   cx - 9 * S + cap, cy + 21 * S + cap], fill=color)
        d.ellipse([cx + 9 * S - cap, cy + 21 * S - cap,
                   cx + 9 * S + cap, cy + 21 * S + cap], fill=color)

    def _draw_loading_dots(self, d, cx, cy, color):
        S = AA
        r = 13 * S
        for i in range(3):
            angle = math.radians(self._loading_angle + i * 120)
            dx = cx + r * math.cos(angle)
            dy = cy + r * math.sin(angle)
            dot_r = 4 * S
            d.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
                      fill=color)

    def _draw_spinner_arcs(self, d, cx, cy, color):
        S = AA
        r = 14 * S
        d.arc([cx - r, cy - r, cx + r, cy + r],
              start=-self._spin_angle - 90, end=-self._spin_angle,
              fill=color, width=int(3.5 * S))
        sr = 8 * S
        d.arc([cx - sr, cy - sr, cx + sr, cy + sr],
              start=self._spin_angle - 60, end=self._spin_angle,
              fill=color, width=int(2.5 * S))

    def _draw_error_icon(self, d, cx, cy):
        S = AA
        r = 16 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#E67E22")
        # Exclamation stem
        lw = int(3.5 * S)
        d.line([(cx, cy - 10 * S), (cx, cy + 3 * S)], fill="white", width=lw)
        cap = lw / 2
        d.ellipse([cx - cap, cy - 10 * S - cap, cx + cap, cy - 10 * S + cap],
                  fill="white")
        d.ellipse([cx - cap, cy + 3 * S - cap, cx + cap, cy + 3 * S + cap],
                  fill="white")
        # Dot
        dot_r = 3 * S
        d.ellipse([cx - dot_r, cy + 8 * S - dot_r,
                   cx + dot_r, cy + 8 * S + dot_r], fill="white")

    def _draw_clock_icon(self, d, cx, cy):
        S = AA
        r = 16 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#E67E22")
        # Face
        face_r = 11 * S
        d.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r],
                  outline="white", width=int(2 * S))
        # Hands
        lw = int(2 * S)
        d.line([(cx, cy), (cx, cy - 8 * S)], fill="white", width=lw)
        d.line([(cx, cy), (cx + 6 * S, cy + 3 * S)], fill="white", width=lw)
        # Center dot
        dot_r = 2 * S
        d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                  fill="white")

    # ── Animations ───────────────────────────────────────────────────

    def _animate_loading(self):
        if self._state != "loading":
            return
        self._loading_angle = (self._loading_angle + 8) % 360
        self._draw()
        self._loading_job = self.root.after(50, self._animate_loading)

    def _animate_pulse(self):
        if self._state != "recording":
            return
        self._pulse_phase = (self._pulse_phase + 1) % 20
        self._wave_phase += 0.3
        self._draw()
        self._pulse_job = self.root.after(50, self._animate_pulse)

    def _animate_spin(self):
        if self._state != "transcribing":
            return
        self._spin_angle = (self._spin_angle + 15) % 360
        self._draw()
        self._spin_job = self.root.after(50, self._animate_spin)

    # ── Drag / Click ─────────────────────────────────────────────────

    def _on_press(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._drag_moved = False

    def _on_drag(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        if abs(dx) > 5 or abs(dy) > 5:
            self._drag_moved = True
        if self._drag_moved:
            x = self.win.winfo_x() + dx
            y = self.win.winfo_y() + dy
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, min(x, sw - self._cur_w))
            y = max(0, min(y, sh - self._cur_h))
            self.win.geometry(f"+{x}+{y}")
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root

    def _on_release(self, event):
        if self._drag_moved:
            if self.on_drag_end:
                self.on_drag_end(self.win.winfo_x(), self.win.winfo_y())
            return

        if self._state == "recording":
            click_x = event.x
            click_y = event.y
            if self._btn_check and self._hit_test(click_x, click_y, *self._btn_check):
                if self.on_stop:
                    self.on_stop()
                return
            if self._btn_cancel and self._hit_test(click_x, click_y, *self._btn_cancel):
                if self.on_cancel:
                    self.on_cancel()
                return
            if self.on_click:
                self.on_click()
            return

        if self.on_click:
            self.on_click()

    def _hit_test(self, x, y, cx, cy, r):
        return (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2

    def _on_right_click(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _on_exit(self):
        self.root.quit()
