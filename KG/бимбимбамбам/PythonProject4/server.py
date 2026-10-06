
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import webbrowser
import threading

DEFAULT_POLYGON = """100,300
250,100
400,250
550,100
700,300
550,500
400,350
250,500"""

DEFAULT_WINDOW = """250,150
550,180
600,400
400,500
200,400"""

def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

def is_convex(poly):
    n = len(poly)
    if n < 3: return False
    if len(set(poly)) < n: return False
    signs = set()
    for i in range(n):
        c = cross(poly[i], poly[(i+1) % n], poly[(i+2) % n])
        if abs(c) > 1e-9:
            signs.add(1 if c > 0 else -1)
    return len(signs) == 1

def centroid(poly):
    return (sum(p[0] for p in poly)/len(poly),
            sum(p[1] for p in poly)/len(poly))

def line_intersection(p1, p2, a, b):
    x1, y1 = p1; x2, y2 = p2
    x3, y3 = a; x4, y4 = b
    denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    if abs(denom) < 1e-12:
        return p2
    t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
    return (round(x1 + t*(x2-x1), 2), round(y1 + t*(y2-y1), 2))

def sutherland_hodgman(subject, clip):
    if not is_convex(clip):
        return None
    center = centroid(clip)
    output = list(subject)
    n = len(clip)
    for i in range(n):
        a = clip[i]
        b = clip[(i+1) % n]
        input_list = output
        output = []
        if not input_list:
            break
        S = input_list[-1]
        for E in input_list:
            c_S = cross(a, b, S) * cross(a, b, center)
            c_E = cross(a, b, E) * cross(a, b, center)
            S_in = c_S >= 0
            E_in = c_E >= 0
            if E_in:
                if not S_in:
                    output.append(line_intersection(S, E, a, b))
                output.append(E)
            elif S_in:
                output.append(line_intersection(S, E, a, b))
            S = E
    return output

def parse_points(text):
    pts = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line: continue
        parts = line.replace(',', ' ').split()
        if len(parts) >= 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    return pts

def pts_svg(points):
    return " ".join(f"{x},{y}" for x, y in points)


def render_page(polygon_text, window_text, polygon, window, clipped, error):
    polygon_pts = pts_svg(polygon)
    window_pts = pts_svg(window)

    clipped_svg = ""
    if clipped:
        clipped_svg = f'<polygon points="{pts_svg(clipped)}" fill="rgba(46,204,113,0.45)" stroke="#2ecc71" stroke-width="3" />'

    error_html = ""
    if error:
        error_html = f'<div class="error">⚠ {error}</div>'

    poly_dots = "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="#e74c3c" />' for x, y in polygon)
    win_dots  = "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="white" />' for x, y in window)

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Отсечение многоугольника</title>
<style>
    body {{ font-family: Arial, sans-serif; background: #2c3e50; color: #ecf0f1; margin: 0; padding: 20px; }}
    h1 {{ text-align: center; margin-bottom: 5px; }}
    .subtitle {{ text-align: center; color: #bdc3c7; margin-top: 0; }}
    .layout {{ display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-top: 20px; }}
    .canvas-wrap {{ background: #34495e; padding: 10px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
    svg {{ background: #1a252f; border-radius: 4px; display: block; }}
    .controls {{ background: #34495e; padding: 20px; border-radius: 8px; min-width: 340px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
    .controls h2 {{ margin-top: 0; }}
    label {{ display: block; margin-top: 15px; font-weight: bold; font-size: 14px; }}
    textarea {{ width: 100%; height: 160px; font-family: monospace; background: #1a252f; color: #ecf0f1;
                border: 1px solid #4a6274; border-radius: 4px; padding: 8px; box-sizing: border-box; resize: vertical; }}
    button {{ margin-top: 15px; padding: 12px 20px; background: #3498db; color: white; border: none;
              border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }}
    button:hover {{ background: #2980b9; }}
    .error {{ background: #c0392b; padding: 12px; border-radius: 4px; margin: 15px auto; max-width: 800px; text-align: center; }}
    .legend {{ margin-top: 15px; display: flex; gap: 15px; font-size: 14px; flex-wrap: wrap; }}
    .legend-item {{ display: flex; align-items: center; gap: 5px; }}
    .color-box {{ width: 15px; height: 15px; border-radius: 3px; }}
    .info {{ margin-top: 15px; font-size: 13px; color: #bdc3c7; line-height: 1.5; }}
</style>
</head>
<body>

<h1>Алгоритм Сазерленда-Ходжмана</h1>

{error_html}

<div class="layout">
    <div class="canvas-wrap">
        <svg width="800" height="600">
            <polygon points="{window_pts}" fill="rgba(255,255,255,0.05)" stroke="white" stroke-width="2" stroke-dasharray="6,4" />
            <polygon points="{polygon_pts}" fill="rgba(231,76,60,0.15)" stroke="#e74c3c" stroke-width="2" />
            {clipped_svg}
            {poly_dots}
            {win_dots}
        </svg>
        <div class="legend">
            <div class="legend-item"><div class="color-box" style="background:#e74c3c"></div> Исходный</div>
            <div class="legend-item"><div class="color-box" style="background:#2ecc71"></div> Отсечённый</div>
            <div class="legend-item"><div class="color-box" style="border:2px dashed white"></div> Окно</div>
        </div>
    </div>

    <div class="controls">
        <h2>Параметры</h2>
        <form method="POST">
            <label>Многоугольник (x,y — по одному на строке):</label>
            <textarea name="polygon">{polygon_text}</textarea>

            <label>Окно (обязательно ВЫПУКЛОЕ):</label>
            <textarea name="window">{window_text}</textarea>

            <button type="submit">Пересчитать</button>
        </form>
        <div class="info">
            <b>Формат:</b> <code>x,y</code> — одна вершина на строку.<br>
            <b>Окно</b> должно быть выпуклым многоугольником.<br>
        </div>
    </div>
</div>

</body>
</html>'''

class Handler(BaseHTTPRequestHandler):
    def _send_html(self, html):
        data = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(404); self.end_headers(); return

        polygon = parse_points(DEFAULT_POLYGON)
        window  = parse_points(DEFAULT_WINDOW)
        clipped = sutherland_hodgman(polygon, window) if is_convex(window) else []
        html = render_page(DEFAULT_POLYGON, DEFAULT_WINDOW, polygon, window, clipped, None)
        self._send_html(html)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        params = parse_qs(body)

        polygon_text = params.get('polygon', [DEFAULT_POLYGON])[0]
        window_text  = params.get('window',  [DEFAULT_WINDOW])[0]

        polygon = parse_points(polygon_text)
        window  = parse_points(window_text)

        error = None
        clipped = []

        if len(polygon) < 3:
            error = "Многоугольник должен содержать минимум 3 точки."
        elif len(window) < 3:
            error = "Окно должно содержать минимум 3 точки."
        elif len(set(window)) < len(window):
            error = "В окне есть дублирующиеся точки!"
        elif not is_convex(window):
            error = "Окно должно быть ВЫПУКЛЫМ!"
        else:
            clipped = sutherland_hodgman(polygon, window) or []

        html = render_page(polygon_text, window_text, polygon, window, clipped, error)
        self._send_html(html)

    def log_message(self, fmt, *args):
        pass  # Отключаем логи, чтобы не спамило


if __name__ == '__main__':
    PORT = 8080
    url = f'http://127.0.0.1:{PORT}/'
    print("=" * 50)
    print("СЕРВЕР ЗАПУЩЕН!")
    print(f"Открой в браузере: {url}")
    print("Остановка: Ctrl+C")
    print("=" * 50)

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")