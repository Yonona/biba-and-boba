import json
import math
import tkinter as tk
from dataclasses import dataclass, asdict
from tkinter import filedialog, messagebox, ttk
from typing import List, Tuple


@dataclass
class Point3D:
    x: float
    y: float
    z: float

    def rotate(self, rx: float, ry: float) -> "Point3D":
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        # X rotation
        y1 = self.y * cx - self.z * sx
        z1 = self.y * sx + self.z * cx
        # Y rotation
        x2 = self.x * cy + z1 * sy
        z2 = -self.x * sy + z1 * cy
        return Point3D(x2, y1, z2)

    def __add__(self, other: "Point3D") -> "Point3D":
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)


@dataclass
class Face:
    indices: Tuple[int, ...]
    name: str


@dataclass
class Polyhedron:
    name: str
    vertices: List[Point3D]
    faces: List[Face]
    fill: str


@dataclass
class FaceRecord:
    poly_name: str
    face_name: str
    indices: Tuple[int, ...]
    vertices: List[Point3D]
    z_avg: float
    z_min: float
    z_max: float
    normal_z: float
    visible: bool


def dot(a: Point3D, b: Point3D) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def cross(a: Point3D, b: Point3D) -> Point3D:
    return Point3D(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def subtract(a: Point3D, b: Point3D) -> Point3D:
    return Point3D(a.x - b.x, a.y - b.y, a.z - b.z)


def face_normal(vertices: List[Point3D]) -> Point3D:
    if len(vertices) < 3:
        return Point3D(0, 0, 0)
    return cross(subtract(vertices[1], vertices[0]), subtract(vertices[2], vertices[0]))


def create_box(name: str, cx: float, cy: float, cz: float, sx: float, sy: float, sz: float, fill: str) -> Polyhedron:
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    v = [
        Point3D(cx - hx, cy - hy, cz - hz),
        Point3D(cx + hx, cy - hy, cz - hz),
        Point3D(cx + hx, cy + hy, cz - hz),
        Point3D(cx - hx, cy + hy, cz - hz),
        Point3D(cx - hx, cy - hy, cz + hz),
        Point3D(cx + hx, cy - hy, cz + hz),
        Point3D(cx + hx, cy + hy, cz + hz),
        Point3D(cx - hx, cy + hy, cz + hz),
    ]
    # Counter-clockwise when viewed from outside.
    faces = [
        Face((0, 3, 2, 1), "нижняя"),
        Face((4, 5, 6, 7), "верхняя"),
        Face((0, 1, 5, 4), "передняя"),
        Face((3, 7, 6, 2), "задняя"),
        Face((0, 4, 7, 3), "левая"),
        Face((1, 2, 6, 5), "правая"),
    ]
    return Polyhedron(name, v, faces, fill)


def create_pyramid(name: str, cx: float, cy: float, cz: float, size: float, height: float, fill: str) -> Polyhedron:
    h = size / 2
    v = [
        Point3D(cx - h, cy - h, cz),
        Point3D(cx + h, cy - h, cz),
        Point3D(cx + h, cy + h, cz),
        Point3D(cx - h, cy + h, cz),
        Point3D(cx, cy, cz + height),
    ]
    faces = [
        Face((0, 3, 2, 1), "основание"),
        Face((0, 1, 4), "грань 1"),
        Face((1, 2, 4), "грань 2"),
        Face((2, 3, 4), "грань 3"),
        Face((3, 0, 4), "грань 4"),
    ]
    return Polyhedron(name, v, faces, fill)


def create_scene() -> List[Polyhedron]:
    return [
        create_box("Куб A", -2.8, 0.0, 0.0, 3.2, 2.6, 2.6, "#6ea8dc"),
        create_box("Куб B", 2.0, 0.4, 2.4, 3.0, 2.4, 2.8, "#e38b7b"),
        create_pyramid("Пирамида C", 0.2, 0.1, 3.2, 3.0, 3.8, "#7fc28b"),
    ]


# Фиксированная ориентация наблюдения (наклон камеры). Одна и та же для
# сортировки граней, определения видимости и проецирования.
VIEW_YAW = -0.55
VIEW_PITCH = 0.35


def to_camera(p: Point3D, yaw: float = VIEW_YAW, pitch: float = VIEW_PITCH) -> Point3D:
    """Перевод точки в систему координат наблюдателя (после поворота сцены).

    В этой системе ось Z направлена от наблюдателя вглубь сцены, поэтому:
      * большая z — точка ближе к наблюдателю;
      * грань видима, если внешняя нормаль имеет положительную z-компоненту.
    """
    cy, sy = math.cos(yaw), math.sin(yaw)
    x1 = p.x * cy + p.z * sy
    z1 = -p.x * sy + p.z * cy
    cx, sx = math.cos(pitch), math.sin(pitch)
    y2 = p.y * cx - z1 * sx
    z2 = p.y * sx + z1 * cx
    return Point3D(x1, y2, z2)


def project_camera(p: Point3D, width: int, height: int, scale: float):
    """Ортогональная проекция точки, уже переведённой в систему наблюдателя."""
    return width / 2 + p.x * scale, height / 2 - p.y * scale


def project(p: Point3D, width: int, height: int, scale: float,
            yaw: float = VIEW_YAW, pitch: float = VIEW_PITCH):
    """Проекция точки мировых координат: наклон камеры, затем ортогональная проекция."""
    q = to_camera(p, yaw, pitch)
    x, y = project_camera(q, width, height, scale)
    return x, y, q.z


def build_face_records(scene: List[Polyhedron], rx: float, ry: float) -> List[FaceRecord]:
    records: List[FaceRecord] = []
    for poly in scene:
        # Поворот сцены пользователем и перевод в систему наблюдателя.
        transformed = [to_camera(p.rotate(rx, ry)) for p in poly.vertices]
        for face in poly.faces:
            pts = [transformed[i] for i in face.indices]
            nz = face_normal(pts).z
            # Наблюдатель расположен на +Z системы наблюдателя, поэтому грань
            # видима, если её внешняя нормаль направлена к наблюдателю (nz > 0).
            records.append(
                FaceRecord(
                    poly.name,
                    face.name,
                    face.indices,
                    pts,
                    sum(p.z for p in pts) / len(pts),
                    min(p.z for p in pts),
                    max(p.z for p in pts),
                    nz,
                    nz > 0,
                )
            )
    # Painter algorithm: farthest average z first, nearest last.
    # This is the requested depth sorting by z-coordinate.
    records.sort(key=lambda r: r.z_avg)
    return records


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Лабораторная работа №5 — Видимость многогранников")
        self.root.geometry("1280x940")
        self.root.minsize(1050, 640)
        self.scene = create_scene()
        self.rx = math.radians(18)
        self.ry = math.radians(-28)
        self.show_control = tk.BooleanVar(value=True)
        self.show_hidden = tk.BooleanVar(value=False)
        self.show_labels = tk.BooleanVar(value=False)
        self.use_backface = tk.BooleanVar(value=False)
        self.scale = tk.DoubleVar(value=72)
        self._pending_fit = True        # подобрать масштаб после первого показа холста
        self.status = tk.StringVar()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Лабораторная работа №5", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(top, text="Вариант 3 · видимость совокупности многогранников на основе сортировки граней по z-координате").pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)

        # Панель управления делаем прокручиваемой: при небольшой высоте окна
        # группа «Отображение» иначе остаётся за пределами видимой области.
        left_holder = ttk.Frame(body, width=300)
        left_holder.pack(side="left", fill="y", padx=(0, 10))
        left_holder.pack_propagate(False)
        left_canvas = tk.Canvas(left_holder, highlightthickness=0, width=285)
        left_scroll = ttk.Scrollbar(left_holder, orient="vertical", command=left_canvas.yview)
        left = ttk.Frame(left_canvas)
        left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>",
                  lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>",
                         lambda e: left_canvas.itemconfigure(left_window, width=e.width))
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")
        left_canvas.bind_all("<MouseWheel>",
                             lambda e: left_canvas.yview_scroll(int(-e.delta / 30), "units"))
        center = ttk.Frame(body)
        center.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body, width=392)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        # Scene controls
        box = ttk.LabelFrame(left, text="Сцена", padding=10)
        box.pack(fill="x")
        ttk.Button(box, text="Восстановить пример", command=self.reset_scene).pack(fill="x")
        ttk.Button(box, text="Добавить куб", command=self.add_cube).pack(fill="x", pady=(6, 0))
        ttk.Button(box, text="Добавить пирамиду", command=self.add_pyramid).pack(fill="x", pady=(6, 0))
        ttk.Button(box, text="Удалить выбранный", command=self.remove_selected).pack(fill="x", pady=(6, 0))
        ttk.Button(box, text="Сохранить сцену", command=self.save_scene).pack(fill="x", pady=(6, 0))
        ttk.Button(box, text="Загрузить сцену", command=self.load_scene).pack(fill="x", pady=(6, 0))
        ttk.Button(box, text="Вписать сцену", command=self.fit_and_refresh).pack(fill="x", pady=(6, 0))

        ttk.Label(box, text="Многогранники:").pack(anchor="w", pady=(10, 3))
        self.poly_list = tk.Listbox(box, height=8, exportselection=False)
        self.poly_list.pack(fill="x")
        self.poly_list.bind("<<ListboxSelect>>", lambda e: self._update_selected_info())

        info = ttk.LabelFrame(left, text="Параметры выбранного", padding=10)
        info.pack(fill="x", pady=(10, 0))
        self.info_var = tk.StringVar(value="Выберите многогранник")
        ttk.Label(info, textvariable=self.info_var, wraplength=250).pack(anchor="w")

        rot = ttk.LabelFrame(left, text="Поворот сцены", padding=10)
        rot.pack(fill="x", pady=(10, 0))
        ttk.Label(rot, text="X, градусы").pack(anchor="w")
        self.rx_scale = ttk.Scale(rot, from_=-180, to=180, variable=tk.DoubleVar(value=math.degrees(self.rx)), command=self._rotation_changed)
        self.rx_scale.pack(fill="x")
        ttk.Label(rot, text="Y, градусы").pack(anchor="w", pady=(7, 0))
        self.ry_scale = ttk.Scale(rot, from_=-180, to=180, variable=tk.DoubleVar(value=math.degrees(self.ry)), command=self._rotation_changed)
        self.ry_scale.pack(fill="x")
        ttk.Button(rot, text="Сбросить поворот", command=self.reset_rotation).pack(fill="x", pady=(8, 0))

        disp = ttk.LabelFrame(left, text="Отображение", padding=10)
        disp.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(disp, text="Показывать каркас", variable=self.show_control, command=self._refresh).pack(anchor="w")
        ttk.Checkbutton(disp, text="Показывать скрытые грани", variable=self.show_hidden, command=self._refresh).pack(anchor="w")
        ttk.Checkbutton(disp, text="Подписывать грани", variable=self.show_labels, command=self._refresh).pack(anchor="w")
        ttk.Checkbutton(disp, text="Отсечение обратных граней", variable=self.use_backface, command=self._refresh).pack(anchor="w")
        ttk.Label(disp, text="Масштаб").pack(anchor="w", pady=(8, 0))
        ttk.Scale(disp, from_=35, to=120, variable=self.scale, command=lambda _: self._refresh()).pack(fill="x")

        self.canvas = tk.Canvas(center, background="#111827", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Sorting table
        table_box = ttk.LabelFrame(right, text="Результат сортировки граней", padding=8)
        table_box.pack(fill="both", expand=True)
        ttk.Label(table_box, text="Дальние грани рисуются первыми, ближние — последними.", wraplength=310).pack(anchor="w", pady=(0, 8))
        cols = ("n", "face", "zavg", "zmin", "zmax")
        self.tree = ttk.Treeview(table_box, columns=cols, show="headings", height=28)
        headers = [("n", "№", 38), ("face", "Грань", 118), ("zavg", "Zср", 65), ("zmin", "Zmin", 65), ("zmax", "Zmax", 70)]
        for col, title, width in headers:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w", padding=(8, 4)).pack(fill="x", side="bottom")

    def _on_canvas_resize(self, _event=None):
        """Первое изменение размеров холста — подбираем масштаб под сцену."""
        if self._pending_fit and self.canvas.winfo_width() > 50:
            self._pending_fit = False
            self.fit_scale()
        self._refresh()

    def fit_scale(self, margin=30.0):
        """Подбор масштаба, при котором сцена целиком помещается на холсте.

        Проекция совмещает начало мировых координат с центром холста, поэтому
        предел масштаба определяется наибольшим выходом проекции за половину
        ширины или высоты холста.
        """
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        camera = [to_camera(v.rotate(self.rx, self.ry))
                  for poly in self.scene for v in poly.vertices]
        if not camera:
            return
        xs = [p.x for p in camera]
        ys = [p.y for p in camera]
        limits = []
        if min(xs) < 0:
            limits.append((w / 2 - margin) / -min(xs))
        if max(xs) > 0:
            limits.append((w / 2 - margin) / max(xs))
        if max(ys) > 0:
            limits.append((h / 2 - margin) / max(ys))
        if min(ys) < 0:
            limits.append((h / 2 - margin) / -min(ys))
        if limits:
            self.scale.set(max(30.0, min(120.0, min(limits))))

    def fit_and_refresh(self):
        self.fit_scale()
        self._refresh()

    def _rotation_changed(self, _=None):
        self.rx = math.radians(float(self.rx_scale.get()))
        self.ry = math.radians(float(self.ry_scale.get()))
        self._refresh()

    def reset_rotation(self):
        self.rx_scale.set(18)
        self.ry_scale.set(-28)
        self._rotation_changed()

    def reset_scene(self):
        self.scene = create_scene()
        self.fit_scale()
        self._refresh()

    def add_cube(self):
        idx = len(self.scene) + 1
        x = (idx % 3 - 1) * 2.5
        z = idx * 0.8
        self.scene.append(create_box(f"Куб {idx}", x, 0, z, 2.5, 2.2, 2.2, "#9b8bd4"))
        self.fit_scale()
        self._refresh()

    def add_pyramid(self):
        idx = len(self.scene) + 1
        self.scene.append(create_pyramid(f"Пирамида {idx}", (idx % 3 - 1) * 2.0, 0, idx * 0.7, 2.7, 3.0, "#d7b36a"))
        self.fit_scale()
        self._refresh()

    def remove_selected(self):
        sel = self.poly_list.curselection()
        if not sel:
            return
        del self.scene[sel[0]]
        self.fit_scale()
        self._refresh()

    def _update_selected_info(self):
        sel = self.poly_list.curselection()
        if not sel:
            self.info_var.set("Выберите многогранник")
            return
        p = self.scene[sel[0]]
        self.info_var.set(f"{p.name}\nВершин: {len(p.vertices)}\nГраней: {len(p.faces)}")

    def _draw_axes(self, w, h):
        origin = project(Point3D(0, 0, 0), w, h, self.scale.get())
        axes = [(Point3D(4, 0, 0), "X"), (Point3D(0, 4, 0), "Y"), (Point3D(0, 0, 4), "Z")]
        ox, oy = origin[0], origin[1]
        for p, label in axes:
            q = project(p, w, h, self.scale.get())
            self.canvas.create_line(ox, oy, q[0], q[1], fill="#64748b", width=1, arrow=tk.LAST)
            self.canvas.create_text(q[0], q[1], text=label, fill="#cbd5e1", font=("TkDefaultFont", 9, "bold"))

    def _refresh(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        self._draw_axes(w, h)
        records = build_face_records(self.scene, self.rx, self.ry)

        # Painter algorithm: the records are already sorted from far to near.
        for rec in records:
            if self.use_backface.get() and not rec.visible:
                continue
            poly = next(p for p in self.scene if p.name == rec.poly_name)
            points = []
            for p in rec.vertices:                      # уже в системе наблюдателя
                q = project_camera(p, w, h, self.scale.get())
                points.extend([q[0], q[1]])
            is_selected = False
            color = poly.fill
            if not rec.visible:
                color = "#263244"
            outline = "#e5e7eb" if rec.visible else "#475569"
            width = 1
            if self.show_hidden.get() or rec.visible:
                self.canvas.create_polygon(points, fill=color, outline=outline, width=width)
            if self.show_labels.get():
                cx = sum(points[0::2]) / len(rec.vertices)
                cy = sum(points[1::2]) / len(rec.vertices)
                self.canvas.create_text(cx, cy, text=f"{rec.poly_name}: {rec.face_name}", fill="#ffffff", font=("TkDefaultFont", 8))

        if self.show_control:
            for poly in self.scene:
                transformed = [to_camera(p.rotate(self.rx, self.ry)) for p in poly.vertices]
                edges = set()
                for face in poly.faces:
                    for i in range(len(face.indices)):
                        a = face.indices[i]
                        b = face.indices[(i + 1) % len(face.indices)]
                        edge = tuple(sorted((a, b)))
                        edges.add(edge)
                for a, b in edges:
                    pa = project_camera(transformed[a], w, h, self.scale.get())
                    pb = project_camera(transformed[b], w, h, self.scale.get())
                    self.canvas.create_line(pa[0], pa[1], pb[0], pb[1], fill="#0f172a", width=2)

        self._update_tree(records)
        self.status.set(
            f"Многогранников: {len(self.scene)}   |   Граней: {len(records)}   |   "
            f"Сортировка: Zср ↑ (дальние → ближние)   |   RX={math.degrees(self.rx):.0f}°   RY={math.degrees(self.ry):.0f}°"
        )
        self.poly_list.delete(0, tk.END)
        for p in self.scene:
            self.poly_list.insert(tk.END, p.name)
        if self.scene:
            self.poly_list.selection_set(0)
            self._update_selected_info()

    def _update_tree(self, records: List[FaceRecord]):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, rec in enumerate(records, 1):
            self.tree.insert("", "end", values=(i, f"{rec.poly_name} / {rec.face_name}", f"{rec.z_avg:.2f}", f"{rec.z_min:.2f}", f"{rec.z_max:.2f}"))

    def save_scene(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = []
        for p in self.scene:
            data.append({
                "name": p.name,
                "fill": p.fill,
                "vertices": [asdict(v) for v in p.vertices],
                "faces": [{"indices": list(f.indices), "name": f.name} for f in p.faces],
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_scene(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            scene = []
            for item in data:
                vertices = [Point3D(float(v["x"]), float(v["y"]), float(v["z"])) for v in item["vertices"]]
                faces = [Face(tuple(int(i) for i in f["indices"]), f.get("name", "грань")) for f in item["faces"]]
                scene.append(Polyhedron(item["name"], vertices, faces, item.get("fill", "#8aa6c1")))
            if not scene:
                raise ValueError("Сцена пуста")
            self.scene = scene
            self.fit_scale()
            self._refresh()
        except Exception as exc:
            messagebox.showerror("Ошибка загрузки", str(exc))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
