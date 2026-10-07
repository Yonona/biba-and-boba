"""Лабораторная работа №2, вариант 9.

Формирование на плоскости B-сплайновой кривой различной степени (1...6)
по задающим точкам с использованием ортогонального проецирования на
плоскость визуализации.

Реализовано без сторонних библиотек:
  * базисные функции B-сплайна по рекуррентной формуле Кокса — де Бура;
  * вычисление точки кривой алгоритмом де Бура;
  * зажатый (clamped) и равномерный периодический узловые векторы;
  * редактирование задающих точек полями ввода и перетаскиванием мышью;
  * одновременное построение кривых всех допустимых степеней;
  * график базисных функций N(i,p)(u) в текущей степени.
"""
import json
import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import List, Sequence, Tuple

# ============================ Математическое ядро ============================

CLAMPED = "clamped"      # зажатый (открытый равномерный) узловой вектор
UNIFORM = "uniform"      # равномерный периодический узловой вектор

KNOT_NAMES = {CLAMPED: "зажатый (clamped)", UNIFORM: "равномерный (uniform)"}


@dataclass
class Point2D:
    """Задающая точка на плоскости."""

    x: float
    y: float


def make_knots(n: int, p: int, kind: str = CLAMPED) -> List[float]:
    """Узловой вектор для n+1 задающих точек и степени p.

    Длина вектора равна n + p + 2. Для зажатого вектора крайние узлы имеют
    кратность p+1, поэтому кривая начинается в P(0) и заканчивается в P(n).
    Для равномерного периодического вектора узлы идут с шагом 1, а область
    определения кривой — [p, n+1].
    """
    if p < 0:
        raise ValueError("степень не может быть отрицательной")
    if n < p:
        raise ValueError("число задающих точек должно быть больше степени")
    if kind == CLAMPED:
        inner = n - p                       # число внутренних узлов
        return ([0.0] * (p + 1)
                + [float(j + 1) for j in range(inner)]
                + [float(inner + 1)] * (p + 1))
    if kind == UNIFORM:
        return [float(i) for i in range(n + p + 2)]
    raise ValueError(f"неизвестный тип узлового вектора: {kind}")


def knot_domain(n: int, p: int, knots: Sequence[float]) -> Tuple[float, float]:
    """Область определения кривой [u_p, u_{n+1}]."""
    return knots[p], knots[n + 1]


def find_span(n: int, p: int, u: float, knots: Sequence[float]) -> int:
    """Индекс пролёта, которому принадлежит параметр u (Piegl & Tiller, A2.1)."""
    if u >= knots[n + 1]:
        return n
    if u <= knots[p]:
        return p
    low, high = p, n + 1
    mid = (low + high) // 2
    while u < knots[mid] or u >= knots[mid + 1]:
        if u < knots[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def basis_functions(span: int, u: float, p: int, knots: Sequence[float]) -> List[float]:
    """Ненулевые базисные функции N(span-p,p)...N(span,p) в точке u (A2.2)."""
    N = [0.0] * (p + 1)
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)
    N[0] = 1.0
    for j in range(1, p + 1):
        left[j] = u - knots[span + 1 - j]
        right[j] = knots[span + j] - u
        saved = 0.0
        for r in range(j):
            denom = right[r + 1] + left[j - r]
            temp = N[r] / denom if denom > 1e-12 else 0.0
            N[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        N[j] = saved
    return N


def bspline_point(points: Sequence[Point2D], p: int, knots: Sequence[float],
                  u: float) -> Point2D:
    """Точка B-сплайна — алгоритм де Бура (Piegl & Tiller, A3.1)."""
    n = len(points) - 1
    span = find_span(n, p, u, knots)
    N = basis_functions(span, u, p, knots)
    x = y = 0.0
    for j in range(p + 1):
        w = N[j]
        pt = points[span - p + j]
        x += w * pt.x
        y += w * pt.y
    return Point2D(x, y)


def basis_value(i: int, p: int, u: float, knots: Sequence[float]) -> float:
    """Базисная функция N(i,p)(u) по рекуррентной формуле Кокса — де Бура.

    Используется для независимой проверки алгоритма де Бура и для построения
    графика базисных функций.
    """
    if p == 0:
        if knots[i] <= u < knots[i + 1]:
            return 1.0
        # правый конец области определения включается по замкнутому интервалу
        if (abs(u - knots[-1]) < 1e-12 and knots[i] <= u <= knots[i + 1]
                and knots[i] < knots[i + 1]):
            return 1.0
        return 0.0
    left_den = knots[i + p] - knots[i]
    right_den = knots[i + p + 1] - knots[i + 1]
    value = 0.0
    if left_den > 1e-12:
        value += (u - knots[i]) / left_den * basis_value(i, p - 1, u, knots)
    if right_den > 1e-12:
        value += (knots[i + p + 1] - u) / right_den * basis_value(i + 1, p - 1, u, knots)
    return value


def all_basis(u: float, n: int, p: int, knots: Sequence[float]) -> List[float]:
    """Значения всех базисных функций N(0,p)...N(n,p) в точке u."""
    return [basis_value(i, p, u, knots) for i in range(n + 1)]


def sample_curve(points: Sequence[Point2D], p: int, knots: Sequence[float],
                 per_span: int = 24) -> List[Point2D]:
    """Табуляция кривой: по per_span точек на каждый ненулевой пролёт."""
    n = len(points) - 1
    a, b = knot_domain(n, p, knots)
    result: List[Point2D] = []
    span = find_span(n, p, a, knots)
    while span <= n:
        u0 = max(knots[span], a)
        u1 = min(knots[span + 1], b)
        if u1 - u0 > 1e-12:
            for j in range(per_span):
                result.append(bspline_point(points, p, knots, u0 + (u1 - u0) * j / per_span))
        span += 1
    result.append(bspline_point(points, p, knots, b))
    return result


def curve_length(points: Sequence[Point2D], p: int, knots: Sequence[float],
                 samples: int = 600) -> float:
    """Длина кривой: численное интегрирование по параметру (метод трапеций)."""
    n = len(points) - 1
    a, b = knot_domain(n, p, knots)
    prev = bspline_point(points, p, knots, a)
    total = 0.0
    for i in range(1, samples + 1):
        u = a + (b - a) * i / samples
        cur = bspline_point(points, p, knots, u)
        total += math.dist((prev.x, prev.y), (cur.x, cur.y))
        prev = cur
    return total


def max_degree(n: int, limit: int = 6) -> int:
    """Наибольшая допустимая степень: не выше limit и не выше n."""
    return max(1, min(limit, n))


def default_points() -> List[Point2D]:
    """Пример задания: 7 точек, образующих S-образную кривую."""
    return [Point2D(-6.0, -0.5), Point2D(-4.2, 2.4), Point2D(-2.0, -2.6),
            Point2D(0.5, 2.8), Point2D(2.6, -2.2), Point2D(4.6, 1.6),
            Point2D(6.4, -0.8)]


# =============================== Интерфейс ===============================

CURVE_COLORS = ["#f2b134", "#69b7ff", "#7fc28b", "#e38b7b", "#9b8bd4", "#4dd0e1"]
BASIS_COLORS = ["#f2b134", "#69b7ff", "#7fc28b", "#e38b7b", "#9b8bd4", "#4dd0e1",
                "#f06292", "#a5d6a7", "#ffd54f", "#90a4ae"]


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Лабораторная работа №2 — B-сплайн кривые")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 700)

        self.points: List[Point2D] = default_points()
        self.entries: List[Tuple[tk.Entry, tk.Entry]] = []

        self.degree = tk.IntVar(value=3)
        self.knot_kind = tk.StringVar(value=CLAMPED)
        self.per_span = tk.IntVar(value=24)
        self.show_all_degrees = tk.BooleanVar(value=False)
        self.show_polygon = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.show_axes = tk.BooleanVar(value=True)
        self.show_knot_marks = tk.BooleanVar(value=False)
        self.point_count = tk.IntVar(value=7)
        self.status = tk.StringVar(value="")
        self.knots_text = tk.StringVar(value="")
        self.props_text = tk.StringVar(value="")

        self.scale = 60.0
        self.offset = (0.0, 0.0)          # мировые координаты центра холста
        self.drag_index = None
        self._pending_fit = True

        self._build_ui()
        self._refresh()

    # --------------------------- построение интерфейса ---------------------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Лабораторная работа №2",
                  font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(top, text="Вариант 9 · B-сплайн кривая степени 1…6 на плоскости "
                            "по задающим точкам").pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)

        # --- левая панель (прокручиваемая) ---
        holder = ttk.Frame(body, width=330)
        holder.pack(side="left", fill="y", padx=(0, 10))
        holder.pack_propagate(False)
        panel_canvas = tk.Canvas(holder, highlightthickness=0, width=315)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=panel_canvas.yview)
        left = ttk.Frame(panel_canvas)
        window = panel_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>",
                  lambda e: panel_canvas.configure(scrollregion=panel_canvas.bbox("all")))
        panel_canvas.bind("<Configure>",
                          lambda e: panel_canvas.itemconfigure(window, width=e.width))
        panel_canvas.configure(yscrollcommand=scroll.set)
        panel_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        panel_canvas.bind_all("<MouseWheel>",
                              lambda e: panel_canvas.yview_scroll(int(-e.delta / 30), "units"))

        self._build_curve_panel(left)
        self._build_points_panel(left)
        self._build_file_panel(left)

        # --- холст ---
        center = ttk.Frame(body)
        center.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(center, background="#111827", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # --- правая панель ---
        right = ttk.Frame(body, width=330)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        knots_box = ttk.LabelFrame(right, text="Узловой вектор", padding=8)
        knots_box.pack(fill="x")
        ttk.Label(knots_box, textvariable=self.knots_text, wraplength=295,
                  justify="left").pack(anchor="w")

        prop_box = ttk.LabelFrame(right, text="Параметры кривой", padding=8)
        prop_box.pack(fill="x", pady=(10, 0))
        ttk.Label(prop_box, textvariable=self.props_text, wraplength=295,
                  justify="left").pack(anchor="w")

        basis_box = ttk.LabelFrame(right, text="Базисные функции N(i,p)(u)", padding=8)
        basis_box.pack(fill="both", expand=True, pady=(10, 0))
        self.basis_canvas = tk.Canvas(basis_box, background="#0b1220",
                                      highlightthickness=0, height=210)
        self.basis_canvas.pack(fill="both", expand=True)

        ttk.Label(self.root, textvariable=self.status, relief="sunken",
                  anchor="w", padding=(8, 4)).pack(fill="x", side="bottom")

    def _build_curve_panel(self, parent):
        box = ttk.LabelFrame(parent, text="Кривая", padding=10)
        box.pack(fill="x")

        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Label(row, text="Степень p:").pack(side="left")
        self.degree_spin = tk.Spinbox(row, from_=1, to=6, width=4,
                                      command=self._degree_changed)
        self.degree_spin.delete(0, "end")
        self.degree_spin.insert(0, "3")
        self.degree_spin.pack(side="left", padx=(6, 0))

        row2 = ttk.Frame(box)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="Точек:").pack(side="left")
        self.count_spin = tk.Spinbox(row2, from_=4, to=10, width=4,
                                     command=self._point_count_changed)
        self.count_spin.delete(0, "end")
        self.count_spin.insert(0, "7")
        self.count_spin.pack(side="left", padx=(6, 0))
        ttk.Button(row2, text="Применить", command=self._point_count_changed).pack(
            side="left", padx=(8, 0))

        ttk.Checkbutton(box, text="Показать все степени 1…6",
                        variable=self.show_all_degrees,
                        command=self._refresh).pack(anchor="w", pady=(8, 0))

        kn = ttk.LabelFrame(parent, text="Узловой вектор", padding=10)
        kn.pack(fill="x", pady=(10, 0))
        ttk.Radiobutton(kn, text="Зажатый (clamped)", value=CLAMPED,
                        variable=self.knot_kind, command=self._refresh).pack(anchor="w")
        ttk.Radiobutton(kn, text="Равномерный периодический", value=UNIFORM,
                        variable=self.knot_kind, command=self._refresh).pack(anchor="w")

        view = ttk.LabelFrame(parent, text="Отображение", padding=10)
        view.pack(fill="x", pady=(10, 0))
        for text, var in [("Задающая ломаная", self.show_polygon),
                          ("Задающие точки", self.show_points),
                          ("Оси и сетка", self.show_axes),
                          ("Отметки узлов", self.show_knot_marks)]:
            ttk.Checkbutton(view, text=text, variable=var,
                            command=self._refresh).pack(anchor="w")
        row3 = ttk.Frame(view)
        row3.pack(fill="x", pady=(6, 0))
        ttk.Label(row3, text="Точек на пролёт:").pack(side="left")
        ttk.Spinbox(row3, from_=4, to=80, width=4, textvariable=self.per_span,
                    command=self._refresh).pack(side="left", padx=(6, 0))
        ttk.Button(view, text="Вписать в холст", command=self.fit_and_refresh).pack(
            fill="x", pady=(8, 0))

    def _build_points_panel(self, parent):
        self.points_box = ttk.LabelFrame(parent, text="Задающие точки (x; y)", padding=10)
        self.points_box.pack(fill="x", pady=(10, 0))
        ttk.Label(self.points_box,
                  text="Координаты можно править в полях или перетаскивать точки мышью.",
                  wraplength=290, justify="left").pack(anchor="w", pady=(0, 6))
        self.editor = ttk.Frame(self.points_box)
        self.editor.pack(fill="x")
        self._rebuild_editor()
        ttk.Button(self.points_box, text="Сбросить пример",
                   command=self._load_example).pack(fill="x", pady=(8, 0))

    def _build_file_panel(self, parent):
        box = ttk.Frame(parent)
        box.pack(fill="x", pady=(10, 0))
        ttk.Button(box, text="Сохранить точки", command=self.save_points).pack(fill="x")
        ttk.Button(box, text="Загрузить точки", command=self.load_points).pack(
            fill="x", pady=(6, 0))

    def _rebuild_editor(self):
        for widget in self.editor.winfo_children():
            widget.destroy()
        self.entries = []
        for i, p in enumerate(self.points):
            ttk.Label(self.editor, text=f"P{i}", width=4).grid(row=i, column=0, pady=1)
            ex = ttk.Entry(self.editor, width=9)
            ey = ttk.Entry(self.editor, width=9)
            ex.insert(0, f"{p.x:g}")
            ey.insert(0, f"{p.y:g}")
            ex.grid(row=i, column=1, padx=(0, 3), pady=1)
            ey.grid(row=i, column=2, pady=1)
            ex.bind("<Return>", lambda _e: self._read_editor())
            ey.bind("<Return>", lambda _e: self._read_editor())
            ex.bind("<FocusOut>", lambda _e: self._read_editor())
            ey.bind("<FocusOut>", lambda _e: self._read_editor())
            self.entries.append((ex, ey))

    # --------------------------- служебные действия ---------------------------
    def _read_editor(self):
        try:
            points = []
            for ex, ey in self.entries:
                points.append(Point2D(float(ex.get().replace(",", ".")),
                                      float(ey.get().replace(",", "."))))
        except ValueError:
            self.status.set("Ошибка: координаты задаются числами, например −2.5")
            return
        self.points = points
        self._refresh()

    def _read_editor_silent(self):
        try:
            for i, (ex, ey) in enumerate(self.entries):
                self.points[i] = Point2D(float(ex.get().replace(",", ".")),
                                         float(ey.get().replace(",", ".")))
        except (ValueError, IndexError):
            pass

    def _sync_editor(self):
        for (ex, ey), p in zip(self.entries, self.points):
            ex.delete(0, "end")
            ex.insert(0, f"{p.x:g}")
            ey.delete(0, "end")
            ey.insert(0, f"{p.y:g}")

    def _degree_changed(self):
        try:
            value = int(float(self.degree_spin.get()))
        except ValueError:
            return
        limit = max_degree(len(self.points) - 1)
        value = max(1, min(limit, value))
        self.degree.set(value)
        self.degree_spin.delete(0, "end")
        self.degree_spin.insert(0, str(value))
        self._refresh()

    def _point_count_changed(self):
        try:
            count = int(float(self.count_spin.get()))
        except ValueError:
            return
        count = max(4, min(10, count))
        self.count_spin.delete(0, "end")
        self.count_spin.insert(0, str(count))
        old = self.points
        new = []
        for i in range(count):
            if i < len(old):
                new.append(Point2D(old[i].x, old[i].y))
            else:
                t = (i + 1) / (count + 1)
                new.append(Point2D(-6.5 + 13.0 * t, 2.6 * math.sin(3.0 * t * math.pi)))
        self.points = new
        self.point_count.set(count)
        limit = max_degree(count - 1)
        if self.degree.get() > limit:
            self.degree.set(limit)
            self.degree_spin.delete(0, "end")
            self.degree_spin.insert(0, str(limit))
        self._rebuild_editor()
        self.fit_scale()
        self._refresh()

    def _load_example(self):
        self.points = default_points()
        self.point_count.set(7)
        self.count_spin.delete(0, "end")
        self.count_spin.insert(0, "7")
        self.degree.set(3)
        self.degree_spin.delete(0, "end")
        self.degree_spin.insert(0, "3")
        self.knot_kind.set(CLAMPED)
        self.show_all_degrees.set(False)
        self._rebuild_editor()
        self.fit_scale()
        self._refresh()

    # --------------------------- работа с файлами ---------------------------
    def save_points(self):
        self._read_editor_silent()
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {"degree": self.degree.get(),
                "knots": self.knot_kind.get(),
                "segments": self.per_span.get(),
                "points": [{"x": p.x, "y": p.y} for p in self.points]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.status.set(f"Сохранено: {path}")

    def load_points(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            points = [Point2D(float(v["x"]), float(v["y"])) for v in data["points"]]
            if len(points) < 4:
                raise ValueError("нужно не менее четырёх точек")
            self.points = points
            count = len(points)
            self.point_count.set(count)
            self.count_spin.delete(0, "end")
            self.count_spin.insert(0, str(count))
            limit = max_degree(count - 1)
            degree = max(1, min(limit, int(data.get("degree", self.degree.get()))))
            self.degree.set(degree)
            self.degree_spin.delete(0, "end")
            self.degree_spin.insert(0, str(degree))
            self.knot_kind.set(data.get("knots", CLAMPED))
            self.per_span.set(max(4, min(80, int(data.get("segments", 24)))))
            self._rebuild_editor()
            self.fit_scale()
            self._refresh()
            self.status.set(f"Загружено: {path}")
        except Exception as exc:                       # noqa: BLE001
            messagebox.showerror("Ошибка загрузки", str(exc))

    # --------------------------- координаты ---------------------------
    def _on_canvas_resize(self, _event=None):
        if self._pending_fit and self.canvas.winfo_width() > 50:
            self._pending_fit = False
            self.fit_scale()
        self._refresh()

    def _world_bounds(self):
        """Габариты задающих точек и построенных кривых."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        for p in self._degrees_to_draw():
            degree, knots = p
            for q in sample_curve(self.points, degree, knots, per_span=8):
                xs.append(q.x)
                ys.append(q.y)
        return min(xs), max(xs), min(ys), max(ys)

    def _degrees_to_draw(self):
        """Список пар (степень, узловой вектор) для текущего режима."""
        n = len(self.points) - 1
        limit = max_degree(n)
        if self.show_all_degrees.get():
            return [(p, make_knots(n, p, self.knot_kind.get()))
                    for p in range(1, limit + 1)]
        p = max(1, min(limit, int(self.degree.get())))
        return [(p, make_knots(n, p, self.knot_kind.get()))]

    def fit_scale(self, margin=34.0):
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        xmin, xmax, ymin, ymax = self._world_bounds()
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        spanx = max(xmax - xmin, 1e-6)
        spany = max(ymax - ymin, 1e-6)
        self.scale = max(4.0, min((w - 2 * margin) / spanx, (h - 2 * margin) / spany))
        self.offset = (cx, cy)

    def fit_and_refresh(self):
        self.fit_scale()
        self._refresh()

    def to_screen(self, p: Point2D) -> Tuple[float, float]:
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        return (w / 2 + (p.x - self.offset[0]) * self.scale,
                h / 2 - (p.y - self.offset[1]) * self.scale)

    def to_world(self, x: float, y: float) -> Point2D:
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        return Point2D(self.offset[0] + (x - w / 2) / self.scale,
                       self.offset[1] - (y - h / 2) / self.scale)

    # --------------------------- перетаскивание точек ---------------------------
    def _pick_point(self, x: float, y: float):
        best, best_d = None, 12.0
        for i, p in enumerate(self.points):
            sx, sy = self.to_screen(p)
            d = math.dist((sx, sy), (x, y))
            if d < best_d:
                best, best_d = i, d
        return best

    def _on_press(self, event):
        index = self._pick_point(event.x, event.y)
        if index is not None:
            self.drag_index = index
            self.canvas.configure(cursor="hand2")
            self.status.set(f"Перетаскивание точки P{index}")

    def _on_drag(self, event):
        if self.drag_index is None:
            return
        world = self.to_world(event.x, event.y)
        self.points[self.drag_index] = world
        self._sync_editor()
        self._refresh(keep_view=True)

    def _on_release(self, _event):
        if self.drag_index is not None:
            self.status.set(f"Точка P{self.drag_index} перемещена")
        self.drag_index = None
        self.canvas.configure(cursor="")

    # --------------------------- отрисовка ---------------------------
    def _refresh(self, keep_view: bool = False):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        if self.show_axes.get():
            self._draw_axes()
        n = len(self.points) - 1
        curves = self._degrees_to_draw()

        if self.show_polygon.get():
            pts = [self.to_screen(p) for p in self.points]
            for a, b in zip(pts, pts[1:]):
                self.canvas.create_line(*a, *b, fill="#8d6e63", width=1, dash=(4, 3))

        for k, (degree, knots) in enumerate(curves):
            color = CURVE_COLORS[k % len(CURVE_COLORS)]
            sampled = sample_curve(self.points, degree, knots,
                                   per_span=max(4, min(80, self.per_span.get())))
            screen = [self.to_screen(q) for q in sampled]
            for a, b in zip(screen, screen[1:]):
                self.canvas.create_line(*a, *b, fill=color, width=2,
                                        capstyle=tk.ROUND)
            if self.show_knot_marks.get():
                a, b = knot_domain(n, degree, knots)
                marks = sorted({round(k, 9) for k in knots if a - 1e-9 <= k <= b + 1e-9})
                for u in marks:
                    q = self.to_screen(bspline_point(self.points, degree, knots, u))
                    r = 3
                    self.canvas.create_oval(q[0] - r, q[1] - r, q[0] + r, q[1] + r,
                                            fill="#e5e7eb", outline="")

        if self.show_points.get():
            for i, p in enumerate(self.points):
                x, y = self.to_screen(p)
                active = (i == self.drag_index)
                r = 6 if active else 5
                self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                        fill="#ffb74d" if not active else "#ff7043",
                                        outline="#0f172a")
                self.canvas.create_text(x + 10, y - 10, text=f"P{i}", anchor="w",
                                        fill="#e8edf2", font=("TkDefaultFont", 9))

        if self.show_all_degrees.get():
            self._draw_legend(curves)

        self._update_panels(curves)
        self._update_status(curves)

    def _draw_axes(self):
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        step = 1.0
        while step * self.scale < 46:
            step *= 2
        while step * self.scale > 170:
            step /= 2
        xmin, xmax, ymin, ymax = self._world_bounds()
        x0, y0 = self.to_screen(Point2D(math.floor(xmin / step) * step,
                                        math.floor(ymin / step) * step))
        x1, y1 = self.to_screen(Point2D(math.ceil(xmax / step) * step,
                                        math.ceil(ymax / step) * step))
        gx = math.floor(xmin / step) * step
        while gx <= xmax + step:
            sx, _ = self.to_screen(Point2D(gx, 0))
            self.canvas.create_line(sx, 0, sx, h, fill="#1f2937")
            self.canvas.create_text(sx + 3, h - 14, text=f"{gx:g}", anchor="w",
                                    fill="#64748b", font=("TkDefaultFont", 8))
            gx += step
        gy = math.floor(ymin / step) * step
        while gy <= ymax + step:
            _, sy = self.to_screen(Point2D(0, gy))
            self.canvas.create_line(0, sy, w, sy, fill="#1f2937")
            self.canvas.create_text(6, sy - 10, text=f"{gy:g}", anchor="w",
                                    fill="#64748b", font=("TkDefaultFont", 8))
            gy += step
        ox, oy = self.to_screen(Point2D(0, 0))
        self.canvas.create_line(ox, 0, ox, h, fill="#475569", width=2)
        self.canvas.create_line(0, oy, w, oy, fill="#475569", width=2)
        self.canvas.create_text(ox + 12, oy - 12, text="X", fill="#94a3b8")
        self.canvas.create_text(ox - 16, oy - 12, text="Y", fill="#94a3b8")

    def _draw_legend(self, curves):
        x, y = 14, 14
        self.canvas.create_rectangle(x - 6, y - 6, x + 150, y + 20 * len(curves) + 6,
                                     fill="#0b1220", outline="#334155")
        for k, (degree, _knots) in enumerate(curves):
            color = CURVE_COLORS[k % len(CURVE_COLORS)]
            yy = y + 20 * k
            self.canvas.create_line(x, yy + 8, x + 26, yy + 8, fill=color, width=3)
            self.canvas.create_text(x + 34, yy + 8, text=f"степень p = {degree}",
                                    anchor="w", fill="#e5e7eb",
                                    font=("TkDefaultFont", 9))

    def _update_panels(self, curves):
        n = len(self.points) - 1
        degree, knots = curves[-1] if len(curves) == 1 else (self.degree.get(), None)
        if len(curves) == 1:
            values = ", ".join(f"{k:g}" for k in knots)
        else:
            values = " — для каждой степени свой вектор (см. таблицу ниже)"
        self.knots_text.set(f"U = [{values}]")

        lines = []
        for k, (p, kn) in enumerate(curves):
            a, b = knot_domain(n, p, kn)
            spans = len({round(u, 9) for u in kn if a < u < b}) + 1
            length = curve_length(self.points, p, kn, samples=300)
            lines.append(f"p = {p}:  пролётов {spans},  u ∈ [{a:g}; {b:g}],  "
                         f"длина ≈ {length:.3f}")
        lines.append(f"Задающих точек: {n + 1};  ненулевых базисных функций "
                     f"в точке: p + 1")
        self.props_text.set("\n".join(lines))

        self._draw_basis(curves)

    def _draw_basis(self, curves):
        c = self.basis_canvas
        c.delete("all")
        w = max(c.winfo_width(), 200)
        h = max(c.winfo_height(), 140)
        n = len(self.points) - 1
        degree, knots = curves[-1]
        a, b = knot_domain(n, degree, knots)
        pad = 26
        samples = 160
        max_val = 1.0
        values = []
        for i in range(n + 1):
            row = []
            for s in range(samples + 1):
                u = a + (b - a) * s / samples
                row.append(basis_value(i, degree, u, knots))
            values.append(row)
            max_val = max(max_val, max(row))
        c.create_line(pad, h - pad, w - 8, h - pad, fill="#334155")
        c.create_line(pad, 14, pad, h - pad, fill="#334155")
        c.create_text(pad - 6, 14, text="1", anchor="e", fill="#64748b",
                      font=("TkDefaultFont", 8))
        c.create_text(w - 8, h - pad + 10, text=f"u={b:g}", anchor="e",
                      fill="#64748b", font=("TkDefaultFont", 8))
        c.create_text(pad, h - pad + 10, text=f"u={a:g}", anchor="w",
                      fill="#64748b", font=("TkDefaultFont", 8))
        # подложка под подписи базисных функций
        c.create_rectangle(w - 46, 6, w - 4, 16 + 13 * (n + 1),
                           fill="#0b1220", outline="#334155")
        for i in range(n + 1):
            color = BASIS_COLORS[i % len(BASIS_COLORS)]
            points = []
            for s in range(samples + 1):
                u = a + (b - a) * s / samples
                x = pad + (w - 8 - pad) * s / samples
                y = (h - pad) - (h - pad - 14) * (values[i][s] / max_val)
                points.extend([x, y])
            c.create_line(*points, fill=color, width=2)
            c.create_text(w - 10, 14 + 13 * i, text=f"N{i}", anchor="e", fill=color,
                          font=("TkDefaultFont", 8))

    def _update_status(self, curves):
        n = len(self.points) - 1
        mode = "все степени" if self.show_all_degrees.get() else f"p = {self.degree.get()}"
        first_p, first_knots = curves[0]
        a, b = knot_domain(n, first_p, first_knots)
        self.status.set(
            f"Задающих точек: {n + 1}   |   {mode}   |   узловой вектор: "
            f"{KNOT_NAMES[self.knot_kind.get()]}   |   u ∈ [{a:g}; {b:g}]   |   "
            f"масштаб: {self.scale:.1f} px/ед.")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
