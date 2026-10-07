import math
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float



def signed_area(poly):
    s = 0.0
    for i in range(len(poly)):
        p1 = poly[i]
        p2 = poly[(i + 1) % len(poly)]
        s += p1.x * p2.y - p2.x * p1.y
    return s / 2.0


def is_convex(poly):
    """Проверка выпуклости простого многоугольника."""
    if len(poly) < 3:
        return False
    sign = 0
    n = len(poly)
    for i in range(n):
        p0, p1, p2 = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cross = (p1.x - p0.x) * (p2.y - p1.y) - (p1.y - p0.y) * (p2.x - p1.x)
        if abs(cross) < 1e-9:
            continue
        s = 1 if cross > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def is_inside(p, edge_start, edge_end, is_cw):
    cross = (edge_end.x - edge_start.x) * (p.y - edge_start.y) - \
            (edge_end.y - edge_start.y) * (p.x - edge_start.x)
    return cross >= 0 if is_cw else cross <= 0


def get_intersection(s, p, edge_start, edge_end):
    dx1 = p.x - s.x
    dy1 = p.y - s.y
    dx2 = edge_end.x - edge_start.x
    dy2 = edge_end.y - edge_start.y
    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < 1e-12:
        return Point(s.x, s.y)
    t = ((edge_start.x - s.x) * dy2 - (edge_start.y - s.y) * dx2) / denom
    return Point(s.x + t * dx1, s.y + t * dy1)


def clip_polygon(subject_polygon, clip_window):
    if len(clip_window) < 3 or len(subject_polygon) < 3:
        return []
    is_cw = signed_area(clip_window) > 0

    output_list = list(subject_polygon)
    for i in range(len(clip_window)):
        edge_start = clip_window[i]
        edge_end = clip_window[(i + 1) % len(clip_window)]

        input_list = output_list
        output_list = []
        if not input_list:
            break

        s = input_list[-1]
        for p in input_list:
            p_in = is_inside(p, edge_start, edge_end, is_cw)
            s_in = is_inside(s, edge_start, edge_end, is_cw)
            if p_in:
                if not s_in:
                    output_list.append(get_intersection(s, p, edge_start, edge_end))
                output_list.append(p)
            elif s_in:
                output_list.append(get_intersection(s, p, edge_start, edge_end))
            s = p
    return output_list



class PolygonClipperApp(tk.Tk):
    SNAP_RADIUS = 10

    def __init__(self):
        super().__init__()
        self.title("Отсечение многоугольника (Сазерленд-Ходжмен)")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.subject_points = []
        self.window_points = []
        self.clipped_points = []
        self.mode = None
        self.current_mouse_pos = (0, 0)
        self.hover = None
        self.drag = None

        self.show_grid = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.show_labels = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="Готово. Выберите режим рисования.")

        self._build_style()
        self._build_ui()

        self.canvas.bind("<Button-1>", self.left_click)
        self.canvas.bind("<B1-Motion>", self.left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.left_release)
        self.canvas.bind("<Button-3>", self.right_click)
        self.canvas.bind("<Motion>", self.mouse_move)
        self.canvas.bind("<BackSpace>", self.undo_last_point)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.focus_set()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("TkDefaultFont", 14, "bold"))
        style.configure("Section.TLabelframe.Label", font=("TkDefaultFont", 10, "bold"))

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root, width=320)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        left.grid_propagate(False)

        ttk.Label(left, text="Отсечение многоугольника",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(left, text="Алгоритм Сазерленда-Ходжмена").pack(anchor="w", pady=(0, 15))

        self._build_mode_panel(left)
        self._build_view_panel(left)
        self._build_help_panel(left)

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(right, bg="#101318", highlightthickness=1,
                                highlightbackground="#333840", cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        ttk.Label(right, textvariable=self.status_text, anchor="w").grid(
            row=1, column=0, sticky="ew", pady=(6, 0))

    def _build_mode_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Управление", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 10))

        self.btn_subject = ttk.Button(
            frame, text="1. Рисовать Исходный (Синий)",
            command=lambda: self.set_mode('subject'))
        self.btn_subject.pack(fill="x", padx=8, pady=4)

        self.btn_window = ttk.Button(
            frame, text="2. Рисовать Окно (Красное)",
            command=lambda: self.set_mode('window'))
        self.btn_window.pack(fill="x", padx=8, pady=4)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=8, pady=8)

        ttk.Button(frame, text="3. Выполнить отсечение",
                   command=self.perform_clip).pack(fill="x", padx=8, pady=4)
        ttk.Button(frame, text="Очистить всё",
                   command=self.clear_all).pack(fill="x", padx=8, pady=(4, 8))

    def _build_view_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Отображение", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(frame, text="Показывать сетку", variable=self.show_grid,
                        command=self.redraw).pack(anchor="w", padx=8, pady=2)
        ttk.Checkbutton(frame, text="Показывать точки", variable=self.show_points,
                        command=self.redraw).pack(anchor="w", padx=8, pady=2)
        ttk.Checkbutton(frame, text="Показывать подписи", variable=self.show_labels,
                        command=self.redraw).pack(anchor="w", padx=8, pady=2)

    def _build_help_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Справка", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 10))
        txt = ("• ЛКМ по пустому месту — новая точка\n"
               "• Зажать ЛКМ на точке — перетащить\n"
               "• ПКМ на точке — удалить её\n"
               "• ПКМ в пустоте — завершить фигуру\n"
               "• Клик по 1-й точке (≥3 точек) — замкнуть\n"
               "• Backspace — отменить последнюю точку")
        ttk.Label(frame, text=txt, justify="left").pack(anchor="w", padx=8, pady=6)

    # ---------- Логика ----------

    def set_mode(self, mode):
        self.mode = mode
        self.canvas.focus_set()
        if mode == 'subject':
            self.status_text.set("Режим: Исходный многоугольник.")
            self.btn_subject.state(['pressed'])
            self.btn_window.state(['!pressed'])
        else:
            self.status_text.set("Режим: Окно отсечения.")
            self.btn_subject.state(['!pressed'])
            self.btn_window.state(['pressed'])

    def _active_points(self):
        if self.mode == 'subject':
            return self.subject_points
        if self.mode == 'window':
            return self.window_points
        return None

    def _find_point_at(self, x, y):
        for which, pts in (('subject', self.subject_points),
                           ('window', self.window_points)):
            for i, p in enumerate(pts):
                if math.hypot(x - p.x, y - p.y) < self.SNAP_RADIUS:
                    return (which, i)
        return None

    def mouse_move(self, event):
        self.current_mouse_pos = (event.x, event.y)
        self.hover = self._find_point_at(event.x, event.y)
        # Курсор: рука на точке, перекрестие в режиме рисования, стрелка иначе
        if self.hover is not None or self.drag is not None:
            self.canvas.config(cursor="hand2")
        elif self.mode:
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="arrow")
        self.redraw()

    def left_click(self, event):
        hit = self._find_point_at(event.x, event.y)

        if hit is not None:
            which, idx = hit

            # Клик по первой точке активного многоугольника — замкнуть
            if self.mode == which:
                pts = self.subject_points if which == 'subject' else self.window_points
                if idx == 0 and len(pts) > 2:
                    self.finish_polygon()
                    return

            # Иначе — начинаем перетаскивание (в любом режиме, любой полигон)
            self.drag = (which, idx)
            self.redraw()
            return

        # Клик по пустому месту — добавляем точку, только если мы в режиме рисования
        if self.mode:
            pts = self._active_points()
            pts.append(Point(event.x, event.y))
            self.redraw()

    def left_drag(self, event):
        if self.drag is None:
            return
        which, idx = self.drag
        pts = self.subject_points if which == 'subject' else self.window_points
        if 0 <= idx < len(pts):
            pts[idx] = Point(event.x, event.y)
            self.current_mouse_pos = (event.x, event.y)
            self.redraw()

    def left_release(self, event):
        if self.drag is not None:
            self.drag = None
            self.redraw()

    def right_click(self, event):
        # ПКМ на существующей точке удалить её
        hit = self._find_point_at(event.x, event.y)
        if hit is not None:
            which, idx = hit
            pts = self.subject_points if which == 'subject' else self.window_points
            if 0 <= idx < len(pts):
                pts.pop(idx)
                self.redraw()
                return
        # ПКМ в пустоте  завершить фигуру
        self.finish_polygon()

    def undo_last_point(self, event):
        if not self.mode:
            return
        pts = self._active_points()
        if pts:
            pts.pop()
            self.redraw()

    def finish_polygon(self):
        if not self.mode:
            return
        pts = self._active_points()
        if len(pts) < 3:
            self.status_text.set("Нужно минимум 3 точки.")
            return
        self.mode = None
        self.btn_subject.state(['!pressed'])
        self.btn_window.state(['!pressed'])
        self.status_text.set("Фигура готова.")
        self.redraw()

    def clear_all(self):
        self.subject_points = []
        self.window_points = []
        self.clipped_points = []
        self.mode = None
        self.hover = None
        self.drag = None
        self.btn_subject.state(['!pressed'])
        self.btn_window.state(['!pressed'])
        self.status_text.set("Очищено.")
        self.redraw()

    def perform_clip(self):
        if len(self.subject_points) < 3:
            messagebox.showerror("Ошибка", "Исходный многоугольник: минимум 3 точки.")
            return
        if len(self.window_points) < 3:
            messagebox.showerror("Ошибка", "Окно отсечения: минимум 3 точки.")
            return
        if not is_convex(self.window_points):
            messagebox.showwarning(
                "Невыпуклое окно",
                "Алгоритм Сазерленда-Ходжмена требует ВЫПУКЛОЕ окно.\n"
                "Результат может быть некорректным.")
        try:
            self.clipped_points = clip_polygon(
                list(self.subject_points), list(self.window_points))
            if not self.clipped_points:
                self.status_text.set("Результат: многоугольник полностью отсечён.")
            else:
                self.status_text.set(
                    f"Отсечение выполнено. Точек: {len(self.clipped_points)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Сбой при отсечении: {e}")
        self.redraw()

    # ---------- Отрисовка ----------

    def redraw(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        self._draw_axes(w, h)

        self._draw_polygon(self.window_points, "window", "#ff6b6b", "#c92a2a", "W")
        self._draw_polygon(self.subject_points, "subject", "#4dabf7", "#1c7ed6", "P")

        if len(self.clipped_points) > 0:
            coords = [(p.x, p.y) for p in self.clipped_points]
            if len(coords) > 1:
                self.canvas.create_polygon(coords, outline="#51cf66",
                                           fill="#2b8a3e", width=2, stipple="gray25")
            if self.show_points.get():
                for i, p in enumerate(self.clipped_points):
                    self.canvas.create_oval(p.x - 3, p.y - 3, p.x + 3, p.y + 3,
                                            fill="#51cf66", outline="#2b8a3e")
                    if self.show_labels.get():
                        self.canvas.create_text(p.x + 10, p.y - 10, text=f"C{i}",
                                                fill="#51cf66", anchor="w",
                                                font=("TkDefaultFont", 8))

    def _draw_polygon(self, points, which, fill_color, outline_color, prefix):
        if not points:
            return
        is_active = (self.mode == which)

        if len(points) > 2:
            coords = [(p.x, p.y) for p in points]
            self.canvas.create_polygon(coords, outline=outline_color,
                                       fill="", width=2)
        if len(points) > 1:
            for i in range(len(points) - 1):
                a, b = points[i], points[i + 1]
                self.canvas.create_line(a.x, a.y, b.x, b.y,
                                        fill=outline_color, width=2)

        # Резиновая нить — только если этот полигон в активном режиме
        if is_active and points:
            last = points[-1]
            mx, my = self.current_mouse_pos
            self.canvas.create_line(last.x, last.y, mx, my,
                                    fill=outline_color, width=1, dash=(4, 4))
            if len(points) > 1:
                first = points[0]
                self.canvas.create_line(mx, my, first.x, first.y,
                                        fill=outline_color, width=1, dash=(4, 4))

        # Кольцо вокруг первой точки (подсказка «клик — замкнуть»)
        if is_active and len(points) > 2:
            p0 = points[0]
            self.canvas.create_oval(p0.x - self.SNAP_RADIUS, p0.y - self.SNAP_RADIUS,
                                    p0.x + self.SNAP_RADIUS, p0.y + self.SNAP_RADIUS,
                                    outline="#ffffff", width=1, dash=(2, 2))

        # Сами точки (рисуем последними, чтобы были поверх всего)
        if self.show_points.get():
            for i, p in enumerate(points):
                is_hover = (self.hover == (which, i))
                is_drag = (self.drag == (which, i))
                r = 6 if (is_hover or is_drag) else 4
                color = "#ffffff" if (is_hover or is_drag) else fill_color
                self.canvas.create_oval(p.x - r, p.y - r, p.x + r, p.y + r,
                                        fill=color, outline=outline_color, width=2)
                if self.show_labels.get():
                    self.canvas.create_text(p.x + 10, p.y - 10,
                                            text=f"{prefix}{i}",
                                            fill=fill_color, anchor="w",
                                            font=("TkDefaultFont", 8))

    def _draw_axes(self, w, h):
        cx, cy = w / 2, h / 2
        if self.show_grid.get():
            for x in range(0, w, 50):
                self.canvas.create_line(x, 0, x, h, fill="#1a1f26")
            for y in range(0, h, 50):
                self.canvas.create_line(0, y, w, y, fill="#1a1f26")
        self.canvas.create_line(20, cy, w - 20, cy, fill="#343a43")
        self.canvas.create_line(cx, 20, cx, h - 20, fill="#343a43")


def main():
    PolygonClipperApp().mainloop()


if __name__ == "__main__":
    main()