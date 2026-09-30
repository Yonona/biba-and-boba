import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass


@dataclass
class Point3D:
    x: float
    y: float
    z: float

    def __add__(self, other):
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, value):
        return Point3D(self.x * value, self.y * value, self.z * value)


# ---------- Mathematical core ----------

def binomial(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def bernstein(n: int, i: int, t: float) -> float:
    return binomial(n, i) * (t ** i) * ((1.0 - t) ** (n - i))


def bezier_surface(control_points, u: float, v: float) -> Point3D:
    """Tensor-product Bezier surface for an arbitrary m x n control polyhedron."""
    rows = len(control_points)
    cols = len(control_points[0])
    m = rows - 1
    n = cols - 1

    result = Point3D(0.0, 0.0, 0.0)
    for i in range(rows):
        bu = bernstein(m, i, u)
        for j in range(cols):
            weight = bu * bernstein(n, j, v)
            result = result + control_points[i][j] * weight
    return result


def rotate_point(p: Point3D, angle_x: float, angle_y: float) -> Point3D:
    """Rotate around X and then Y, matching the two GUI controls."""
    ax = math.radians(angle_x)
    ay = math.radians(angle_y)

    # X rotation
    cy = math.cos(ax)
    sy = math.sin(ax)
    y1 = p.y * cy - p.z * sy
    z1 = p.y * sy + p.z * cy
    x1 = p.x

    # Y rotation
    cx = math.cos(ay)
    sx = math.sin(ay)
    x2 = x1 * cx + z1 * sx
    z2 = -x1 * sx + z1 * cx
    return Point3D(x2, y1, z2)


def project_orthographic(p: Point3D, width: int, height: int, scale: float):
    """Simple orthographic projection onto the XY display plane."""
    return width / 2.0 + p.x * scale, height / 2.0 - p.y * scale


def sample_surface(control_points, steps: int):
    """Return a rectangular sampled grid of the Bezier surface."""
    return [
        [bezier_surface(control_points, i / steps, j / steps) for j in range(steps + 1)]
        for i in range(steps + 1)
    ]


def bounds(points):
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


# ---------- GUI ----------

DEFAULT_POINTS = [
    [Point3D(-3, -2, 0), Point3D(-1, -2, 1), Point3D(1, -2, 1), Point3D(3, -2, 0)],
    [Point3D(-3, 0, 1), Point3D(-1, 0, 3), Point3D(1, 0, 3), Point3D(3, 0, 1)],
    [Point3D(-3, 2, 0), Point3D(-1, 2, 2), Point3D(1, 2, 2), Point3D(3, 2, 0)],
]


class BezierSurfaceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа №3 — Поверхность Безье")
        self.geometry("1250x780")
        self.minsize(1000, 650)

        self.rows = 3
        self.cols = 4
        self.control_points = [row[:] for row in DEFAULT_POINTS]
        self.entries = []

        self.angle_x = tk.DoubleVar(value=25)
        self.angle_y = tk.DoubleVar(value=-35)
        self.surface_steps = tk.IntVar(value=20)
        self.show_control = tk.BooleanVar(value=True)
        self.show_surface = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.auto_scale = tk.BooleanVar(value=True)
        self.scale = tk.DoubleVar(value=75)
        self.status = tk.StringVar(value="Готово")

        self._build_style()
        self._build_ui()
        self._rebuild_editor()
        self.redraw()

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

        left = ttk.Frame(root, width=390)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        left.grid_propagate(False)

        ttk.Label(left, text="Поверхность Безье", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(left, text="Вариант 3 · произвольный задающий многогранник").pack(anchor="w", pady=(0, 10))

        self._build_dimension_panel(left)
        self._build_transform_panel(left)
        self._build_view_panel(left)
        self._build_point_editor(left)
        self._build_file_panel(left)

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(right, bg="#101318", highlightthickness=1, highlightbackground="#333840")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

        ttk.Label(right, textvariable=self.status, anchor="w").grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def _build_dimension_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Задающий многогранник", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 8))

        row = ttk.Frame(frame)
        row.pack(fill="x", padx=8, pady=8)
        ttk.Label(row, text="Строк: ").pack(side="left")
        self.rows_spin = tk.Spinbox(row, from_=2, to=8, width=4, command=self._dimensions_changed)
        self.rows_spin.delete(0, "end")
        self.rows_spin.insert(0, str(self.rows))
        self.rows_spin.pack(side="left", padx=(2, 12))
        ttk.Label(row, text="Столбцов: ").pack(side="left")
        self.cols_spin = tk.Spinbox(row, from_=2, to=8, width=4, command=self._dimensions_changed)
        self.cols_spin.delete(0, "end")
        self.cols_spin.insert(0, str(self.cols))
        self.cols_spin.pack(side="left", padx=2)
        ttk.Button(frame, text="Применить размеры", command=self._dimensions_changed).pack(fill="x", padx=8, pady=(0, 8))

    def _build_transform_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Поворот поверхности", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 8))

        self._slider(frame, "X", self.angle_x)
        self._slider(frame, "Y", self.angle_y)
        ttk.Button(frame, text="Сбросить поворот", command=self._reset_rotation).pack(fill="x", padx=8, pady=(3, 8))

    def _slider(self, parent, name, variable):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=8, pady=3)
        ttk.Label(row, text=f"Ось {name}:", width=7).pack(side="left")
        scale = ttk.Scale(row, from_=-180, to=180, variable=variable, command=lambda _v: self.redraw())
        scale.pack(side="left", fill="x", expand=True, padx=5)
        value = ttk.Label(row, textvariable=variable, width=7)
        value.pack(side="right")

    def _build_view_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Отображение", style="Section.TLabelframe")
        frame.pack(fill="x", pady=(0, 8))

        for text, var in [("Показывать поверхность", self.show_surface),
                          ("Показывать контрольный многогранник", self.show_control),
                          ("Показывать сетку поверхности", self.show_grid),
                          ("Автомасштаб", self.auto_scale)]:
            ttk.Checkbutton(frame, text=text, variable=var, command=self.redraw).pack(anchor="w", padx=8, pady=2)

        row = ttk.Frame(frame)
        row.pack(fill="x", padx=8, pady=(5, 8))
        ttk.Label(row, text="Сегментов сетки:").pack(side="left")
        spin = tk.Spinbox(row, from_=4, to=60, textvariable=self.surface_steps, width=5, command=self.redraw)
        spin.pack(side="left", padx=6)
        ttk.Button(row, text="Обновить", command=self.redraw).pack(side="right")

    def _build_point_editor(self, parent):
        frame = ttk.LabelFrame(parent, text="Координаты контрольных точек", style="Section.TLabelframe")
        frame.pack(fill="both", expand=True, pady=(0, 8))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="P[i,j] = (X, Y, Z). Изменение координаты сразу обновляет поверхность.").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.editor = ttk.Frame(frame)
        self.editor.grid(row=1, column=0, sticky="nsew", padx=5, pady=3)

    def _build_file_panel(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x")
        ttk.Button(frame, text="Пример", command=self._load_example).pack(side="left")
        ttk.Button(frame, text="Сохранить точки", command=self._save_points).pack(side="left", padx=5)
        ttk.Button(frame, text="Загрузить точки", command=self._load_points).pack(side="left")

    def _rebuild_editor(self):
        for widget in self.editor.winfo_children():
            widget.destroy()
        self.entries = [[None for _ in range(self.cols)] for _ in range(self.rows)]

        # Scrollable canvas for the coordinate matrix.
        outer = tk.Canvas(self.editor, highlightthickness=0, height=170)
        scrollbar = ttk.Scrollbar(self.editor, orient="vertical", command=outer.yview)
        body = ttk.Frame(outer)
        body.bind("<Configure>", lambda e: outer.configure(scrollregion=outer.bbox("all")))
        outer.create_window((0, 0), window=body, anchor="nw")
        outer.configure(yscrollcommand=scrollbar.set)
        outer.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for j in range(self.cols):
            ttk.Label(body, text=f"j={j}", width=12).grid(row=0, column=j + 1, padx=2, pady=2)
        for i in range(self.rows):
            ttk.Label(body, text=f"i={i}", width=5).grid(row=i + 1, column=0, padx=2)
            for j in range(self.cols):
                p = self.control_points[i][j]
                entry = ttk.Entry(body, width=12)
                entry.insert(0, f"{p.x:g};{p.y:g};{p.z:g}")
                entry.grid(row=i + 1, column=j + 1, padx=2, pady=2)
                entry.bind("<Return>", lambda _e: self._read_editor())
                entry.bind("<FocusOut>", lambda _e: self._read_editor())
                self.entries[i][j] = entry

    def _read_editor(self):
        try:
            new_points = []
            for i in range(self.rows):
                row = []
                for j in range(self.cols):
                    values = [float(v.strip()) for v in self.entries[i][j].get().replace(",", ";").split(";")]
                    if len(values) != 3:
                        raise ValueError("ожидается X;Y;Z")
                    row.append(Point3D(*values))
                new_points.append(row)
            self.control_points = new_points
            self.redraw()
            self.status.set("Координаты контрольных точек обновлены")
        except ValueError:
            self.status.set("Ошибка: координаты задаются в формате X;Y;Z")

    def _dimensions_changed(self):
        try:
            new_rows = int(self.rows_spin.get())
            new_cols = int(self.cols_spin.get())
            if not (2 <= new_rows <= 8 and 2 <= new_cols <= 8):
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Размеры должны быть целыми числами от 2 до 8.")
            return

        # Preserve existing points and generate a smooth default for newly created cells.
        old = self.control_points
        self.rows, self.cols = new_rows, new_cols
        self.control_points = []
        for i in range(new_rows):
            row = []
            x = -3.0 + 6.0 * i / max(1, new_rows - 1)
            for j in range(new_cols):
                y = -3.0 + 6.0 * j / max(1, new_cols - 1)
                z = 2.0 * math.sin(math.pi * i / max(1, new_rows - 1)) * math.sin(math.pi * j / max(1, new_cols - 1))
                if i < len(old) and j < len(old[0]):
                    p = old[i][j]
                    row.append(Point3D(p.x, p.y, p.z))
                else:
                    row.append(Point3D(x, y, z))
            self.control_points.append(row)
        self._rebuild_editor()
        self.redraw()

    def _reset_rotation(self):
        self.angle_x.set(25)
        self.angle_y.set(-35)
        self.redraw()

    def _load_example(self):
        self.rows, self.cols = 3, 4
        self.rows_spin.delete(0, "end")
        self.rows_spin.insert(0, "3")
        self.cols_spin.delete(0, "end")
        self.cols_spin.insert(0, "4")
        self.control_points = [row[:] for row in DEFAULT_POINTS]
        self._rebuild_editor()
        self._reset_rotation()

    def _save_points(self):
        self._read_editor()
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{self.rows} {self.cols}\n")
            for row in self.control_points:
                f.write(" ".join(f"{p.x};{p.y};{p.z}" for p in row) + "\n")
        self.status.set(f"Сохранено: {path}")

    def _load_points(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                rows, cols = map(int, f.readline().split())
                points = []
                for _ in range(rows):
                    parts = f.readline().split()
                    if len(parts) != cols:
                        raise ValueError("неверное число точек")
                    points.append([Point3D(*map(float, item.split(";"))) for item in parts])
            if not (2 <= rows <= 8 and 2 <= cols <= 8):
                raise ValueError("размер должен быть от 2 до 8")
            self.rows, self.cols, self.control_points = rows, cols, points
            self.rows_spin.delete(0, "end"); self.rows_spin.insert(0, str(rows))
            self.cols_spin.delete(0, "end"); self.cols_spin.insert(0, str(cols))
            self._rebuild_editor(); self.redraw()
            self.status.set(f"Загружено: {path}")
        except Exception as exc:
            messagebox.showerror("Ошибка загрузки", str(exc))

    def _get_scale(self, rotated_control):
        if not self.auto_scale.get():
            return self.scale.get()
        all_points = list(rotated_control)
        if not all_points:
            return 50
        xmin, xmax, ymin, ymax, zmin, zmax = bounds(all_points)
        span = max(xmax - xmin, ymax - ymin, zmax - zmin, 1.0)
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        return min(w, h) * 0.72 / span

    def redraw(self):
        if not hasattr(self, "canvas"):
            return
        self._read_editor_silent()
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 300)

        # Background grid / axes for orientation.
        self._draw_axes(width, height)

        rx = float(self.angle_x.get())
        ry = float(self.angle_y.get())
        control_rot = [[rotate_point(p, rx, ry) for p in row] for row in self.control_points]
        flat_control = [p for row in control_rot for p in row]
        scale = self._get_scale(flat_control)

        def project(p):
            return project_orthographic(p, width, height, scale)

        if self.show_control.get():
            self._draw_control_polyhedron(control_rot, project)

        surface = sample_surface(self.control_points, max(4, min(60, int(self.surface_steps.get()))))
        surface_rot = [[rotate_point(p, rx, ry) for p in row] for row in surface]

        if self.show_surface.get():
            self._draw_surface(surface_rot, project)

        # Redraw control points last for clarity.
        if self.show_control.get():
            for i, row in enumerate(control_rot):
                for j, p in enumerate(row):
                    x, y = project(p)
                    r = 4
                    self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#ffb74d", outline="")
                    self.canvas.create_text(x+8, y-8, text=f"P{i},{j}", fill="#e8edf2", anchor="w", font=("TkDefaultFont", 8))

        self.status.set(f"Безье: {self.rows}×{self.cols} контрольных точек · поворот X={rx:.1f}°, Y={ry:.1f}°")

    def _read_editor_silent(self):
        if not self.entries:
            return
        try:
            for i in range(self.rows):
                for j in range(self.cols):
                    values = [float(v.strip()) for v in self.entries[i][j].get().replace(",", ";").split(";")]
                    if len(values) == 3:
                        self.control_points[i][j] = Point3D(*values)
        except (ValueError, IndexError):
            pass

    def _draw_axes(self, width, height):
        cx, cy = width / 2, height / 2
        self.canvas.create_line(20, cy, width-20, cy, fill="#343a43", width=1)
        self.canvas.create_line(cx, 20, cx, height-20, fill="#343a43", width=1)
        self.canvas.create_text(width-28, cy-10, text="X", fill="#69727d")
        self.canvas.create_text(cx+10, 28, text="Y", fill="#69727d")

    def _draw_control_polyhedron(self, grid, project):
        # Edges along both parameter directions form the characteristic/control grid.
        for i in range(len(grid)):
            for j in range(len(grid[i]) - 1):
                a, b = project(grid[i][j]), project(grid[i][j+1])
                self.canvas.create_line(*a, *b, fill="#8d6e63", width=1, dash=(3, 3))
        for j in range(len(grid[0])):
            for i in range(len(grid) - 1):
                a, b = project(grid[i][j]), project(grid[i+1][j])
                self.canvas.create_line(*a, *b, fill="#8d6e63", width=1, dash=(3, 3))

    def _draw_surface(self, grid, project):
        rows, cols = len(grid), len(grid[0])
        # Surface mesh: u-lines and v-lines. The mesh is the linear approximation of the sampled surface.
        if self.show_grid.get():
            for i in range(rows):
                for j in range(cols - 1):
                    a, b = project(grid[i][j]), project(grid[i][j+1])
                    self.canvas.create_line(*a, *b, fill="#69b7ff", width=1)
            for j in range(cols):
                for i in range(rows - 1):
                    a, b = project(grid[i][j]), project(grid[i+1][j])
                    self.canvas.create_line(*a, *b, fill="#69b7ff", width=1)
        else:
            # Outline only.
            for edge in (grid[0], grid[-1], [grid[i][0] for i in range(rows)], [grid[i][-1] for i in range(rows)]):
                pts = [project(p) for p in edge]
                for a, b in zip(pts, pts[1:]):
                    self.canvas.create_line(*a, *b, fill="#69b7ff", width=2)


def main():
    app = BezierSurfaceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
