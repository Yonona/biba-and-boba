
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

POINTS = [
    (100, 380),
    (200, 200),
    (320, 430),
    (450, 170),
    (580, 400),
    (700, 220),
    (800, 360),
]
N_POINTS = len(POINTS)
N = N_POINTS - 1  # n = 6

def make_knot_vector(n, k):
    m = n - k + 2
    knots = []
    for j in range(n + 1 + k):
        if j < k:
            knots.append(0.0)
        elif j > n:
            knots.append(float(m))
        else:
            knots.append(float(j - k + 1))
    return knots


def basis(i, k, t, knots):
    if k == 1:
        if knots[i] <= t < knots[i + 1]:
            return 1.0
        if t == knots[-1] and knots[i] <= t <= knots[i + 1]:
            return 1.0
        return 0.0

    d1 = knots[i + k - 1] - knots[i]
    left = (t - knots[i]) / d1 * basis(i, k - 1, t, knots) if d1 else 0.0

    d2 = knots[i + k] - knots[i + 1]
    right = (knots[i + k] - t) / d2 * basis(i + 1, k - 1, t, knots) if d2 else 0.0

    return left + right


def bspline_point(t, k, knots):
    x = y = 0.0
    for i in range(N_POINTS):
        w = basis(i, k, t, knots)
        x += POINTS[i][0] * w
        y += POINTS[i][1] * w
    return x, y


def build_curve(k, samples_per_unit=250):
    knots = make_knot_vector(N, k)
    t_min, t_max = knots[k - 1], knots[N + 1]
    total = max(2, int((t_max - t_min) * samples_per_unit))
    pts = [
        bspline_point(t_min + (t_max - t_min) * s / total, k, knots)
        for s in range(total + 1)
    ]
    return pts, knots


HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            index_path = os.path.join(HERE, "index.html")
            if not os.path.exists(index_path):
                self._send(500, "index.html not found next to app.py", "text/plain")
                return
            with open(index_path, "r", encoding="utf-8") as f:
                html = f.read()
            self._send(200, html, "text/html")
            return
        if parsed.path == "/curve":
            qs = parse_qs(parsed.query)
            try:
                k = int(qs.get("k", ["4"])[0])
            except ValueError:
                k = 4
            if not (2 <= k <= N_POINTS):
                k = 4

            curve, knots = build_curve(k, samples_per_unit=250)

            payload = {
                "k": k,
                "points": [[round(x, 3), round(y, 3)] for x, y in POINTS],
                "curve":  [[round(x, 3), round(y, 3)] for x, y in curve],
                "knots":  knots,
            }
            self._send(200, json.dumps(payload), "application/json")
            return

        # ---- 404 ----
        self._send(404, "Not found", "text/plain")

    def log_message(self, fmt, *args):
        pass  # тише в консоли


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"В-сплайн сервер запущен:  http://localhost:{port}")
    print("Ctrl+C — остановить.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")