import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox, ttk

# --- Геометрические функции ---

def rotation_matrix_axis(axis_dir, angle_deg):
    """Матрица поворота вокруг оси с направлением axis_dir на угол angle_deg."""
    angle = np.radians(angle_deg)
    k = np.array(axis_dir, dtype=float)
    k = k / np.linalg.norm(k)
    kx, ky, kz = k
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    R = np.array([
        [t*kx*kx + c,      t*kx*ky - s*kz, t*kx*kz + s*ky],
        [t*kx*ky + s*kz,   t*ky*ky + c,    t*ky*kz - s*kx],
        [t*kx*kz - s*ky,   t*ky*kz + s*kx, t*kz*kz + c]
    ])
    return R

def rotate_points(points, axis_point, axis_dir, angle_deg):
    """Поворачивает точки (N,3) вокруг оси."""
    shifted = points - np.array(axis_point)
    R = rotation_matrix_axis(axis_dir, angle_deg)
    rotated = np.dot(shifted, R.T)
    return rotated + np.array(axis_point)

# --- Построение тел ---

def create_cube(center=(0,0,0), size=2):
    s = size / 2
    vertices = np.array([
        [-s, -s, -s], [ s, -s, -s], [ s,  s, -s], [-s,  s, -s],
        [-s, -s,  s], [ s, -s,  s], [ s,  s,  s], [-s,  s,  s]
    ]) + np.array(center)
    edges = [[0,1], [1,2], [2,3], [3,0],
             [4,5], [5,6], [6,7], [7,4],
             [0,4], [1,5], [2,6], [3,7]]
    return vertices, edges

def create_tetrahedron(center=(0,0,0), size=2):
    s = size / 2
    vertices = np.array([
        [0, 0, s], [s, 0, -s/3], [-s/2, s*np.sqrt(3)/2, -s/3], [-s/2, -s*np.sqrt(3)/2, -s/3]
    ]) * 1.5 + np.array(center)
    edges = [[0,1], [0,2], [0,3], [1,2], [2,3], [3,1]]
    return vertices, edges

# --- Главное приложение ---

class RotationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Поворот тела вокруг произвольной оси")

        # Исходное тело
        self.vertices, self.edges = create_cube(center=(0,0,0), size=2)
        self.body_name = "Куб"

        # Переменные для осей и угла (DoubleVar для связи с полями ввода)
        default_A = [0.0, -2.0, 0.0]
        default_B = [0.0,  2.0, 0.0]
        self.ax_A = [tk.DoubleVar(value=default_A[i]) for i in range(3)]
        self.ax_B = [tk.DoubleVar(value=default_B[i]) for i in range(3)]
        self.angle_var = tk.DoubleVar(value=45.0)

        # Интерфейс
        self.create_widgets()

        # График
        self.fig = plt.Figure(figsize=(6, 6), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.update_plot()

    def create_widgets(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Выбор тела
        tk.Label(control_frame, text="Тело:").grid(row=0, column=0, sticky='w')
        self.body_choice = ttk.Combobox(control_frame, values=["Куб", "Тетраэдр"], state="readonly")
        self.body_choice.current(0)
        self.body_choice.grid(row=0, column=1, padx=5, pady=5)
        self.body_choice.bind("<<ComboboxSelected>>", self.on_body_change)

        # Точка A
        tk.Label(control_frame, text="Точка A (x, y, z):").grid(row=1, column=0, columnspan=2, sticky='w')
        for i, label in enumerate(['x', 'y', 'z']):
            tk.Label(control_frame, text=label).grid(row=2+i, column=0, sticky='e')
            entry = tk.Entry(control_frame, textvariable=self.ax_A[i], width=8)
            entry.grid(row=2+i, column=1, padx=5, pady=2)

        # Точка B
        tk.Label(control_frame, text="Точка B (x, y, z):").grid(row=5, column=0, columnspan=2, sticky='w')
        for i, label in enumerate(['x', 'y', 'z']):
            tk.Label(control_frame, text=label).grid(row=6+i, column=0, sticky='e')
            entry = tk.Entry(control_frame, textvariable=self.ax_B[i], width=8)
            entry.grid(row=6+i, column=1, padx=5, pady=2)

        # Угол
        tk.Label(control_frame, text="Угол (градусы):").grid(row=9, column=0, sticky='e')
        entry = tk.Entry(control_frame, textvariable=self.angle_var, width=8)
        entry.grid(row=9, column=1, padx=5, pady=5)

        # Кнопки
        tk.Button(control_frame, text="Повернуть", command=self.update_plot).grid(row=10, column=0, columnspan=2, pady=10)
        tk.Button(control_frame, text="Сброс", command=self.reset).grid(row=11, column=0, columnspan=2, pady=5)

        tk.Label(control_frame, text="Синий – исходное тело,\nКрасный – повёрнутое").grid(row=12, column=0, columnspan=2, pady=10)

    def on_body_change(self, event):
        choice = self.body_choice.get()
        if choice == "Куб":
            self.vertices, self.edges = create_cube(center=(0,0,0), size=2)
            self.body_name = "Куб"
        else:
            self.vertices, self.edges = create_tetrahedron(center=(0,0,0), size=2)
            self.body_name = "Тетраэдр"
        self.update_plot()

    def reset(self):
        """Сбрасывает параметры к начальным значениям и обновляет график."""
        # Устанавливаем значения в полях ввода
        default_A = [0.0, -2.0, 0.0]
        default_B = [0.0,  2.0, 0.0]
        for i in range(3):
            self.ax_A[i].set(default_A[i])
            self.ax_B[i].set(default_B[i])
        self.angle_var.set(45.0)

        # Возвращаем тело на куб
        self.body_choice.current(0)
        self.vertices, self.edges = create_cube(center=(0,0,0), size=2)
        self.body_name = "Куб"

        self.update_plot()

    def get_axis_from_input(self):
        """Считывает координаты из полей ввода (возвращает кортеж из двух np.array)."""
        try:
            A = np.array([v.get() for v in self.ax_A])
            B = np.array([v.get() for v in self.ax_B])
            return A, B
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Некорректные координаты:\n{e}")
            raise

    def update_plot(self):
        try:
            A, B = self.get_axis_from_input()
            angle = self.angle_var.get()

            if np.allclose(A, B):
                messagebox.showerror("Ошибка", "Точки A и B совпадают! Ось не определена.")
                return

            axis_dir = B - A
            rotated_vertices = rotate_points(self.vertices, A, axis_dir, angle)

            self.ax.clear()
            self.draw_body(self.ax, self.vertices, self.edges, color='blue', label='Исходное')
            self.draw_body(self.ax, rotated_vertices, self.edges, color='red', label='Повёрнутое')
            self.ax.plot([A[0], B[0]], [A[1], B[1]], [A[2], B[2]], 
                         color='green', linewidth=2, label='Ось поворота')

            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_zlabel('Z')
            self.ax.set_title(f'Поворот {self.body_name} на {angle:.1f}°')
            self.ax.legend()
            self.ax.set_xlim(-3, 3)
            self.ax.set_ylim(-3, 3)
            self.ax.set_zlim(-3, 3)
            self.ax.set_box_aspect([1,1,1])
            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def draw_body(self, ax, vertices, edges, color='blue', label=''):
        ax.scatter(vertices[:,0], vertices[:,1], vertices[:,2], color=color, s=20)
        for edge in edges:
            pts = vertices[edge]
            ax.plot(pts[:,0], pts[:,1], pts[:,2], color=color, linewidth=1.5)
        if label:
            center = np.mean(vertices, axis=0)
            ax.text(center[0], center[1], center[2], label, color=color, fontsize=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = RotationApp(root)
    root.mainloop()
