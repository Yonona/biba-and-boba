from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Трассировка лучей — интерактив</title>
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        background: #1e272e; color: #d2dae2;
        margin: 0; padding: 20px;
        display: flex; flex-direction: column; align-items: center;
    }
    h1 { color: #f53b57; margin: 0 0 5px; }
    .subtitle { color: #808e9b; margin: 0 0 15px; font-size: 14px; }
    .layout { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; }
    .canvas-wrap { background: #2c3e50; padding: 10px; border-radius: 12px;
                   box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    canvas { display: block; border-radius: 8px; cursor: grab; }
    canvas.dragging { cursor: grabbing; }
    .panel { background: #2c3e50; padding: 18px; border-radius: 12px;
             min-width: 260px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .panel h3 { margin: 0 0 12px; color: #f53b57; font-size: 15px; }
    .row { margin-bottom: 12px; font-size: 13px; }
    .row label { display: block; margin-bottom: 4px; color: #bdc3c7; }
    .row input[type=range] { width: 100%; }
    .row .val { float: right; color: #f53b57; font-family: monospace; }
    .row input[type=checkbox] { transform: scale(1.3); margin-right: 8px; vertical-align: middle; }
    .hint { color: #808e9b; font-size: 12px; line-height: 1.6; margin-top: 15px;
            border-top: 1px solid #4a6274; padding-top: 12px; }
    .hint b { color: #d2dae2; }
    .fps { color: #2ecc71; font-family: monospace; font-size: 12px; text-align: right; }
</style>
</head>
<body>

<div class="layout">
    <div class="canvas-wrap">
        <canvas id="main" width="800" height="600"></canvas>
        <div class="fps" id="fps">—</div>
    </div>

    <div class="panel">
        <h3>💡 Источник света</h3>
        <div class="row">
            <label>X <span class="val" id="lxVal">5.0</span></label>
            <input type="range" id="lx" min="-15" max="15" step="0.1" value="5">
        </div>
        <div class="row">
            <label>Y <span class="val" id="lyVal">8.0</span></label>
            <input type="range" id="ly" min="0.5" max="15" step="0.1" value="8">
        </div>
        <div class="row">
            <label>Z <span class="val" id="lzVal">-5.0</span></label>
            <input type="range" id="lz" min="-15" max="15" step="0.1" value="-5">
        </div>

        <h3 style="margin-top:18px;">🔵 Объекты</h3>
        <div class="row">
            <label><input type="checkbox" id="s0" checked> обычная</label>
        </div>
        <div class="row">
            <label><input type="checkbox" id="s1" checked> зеркало</label>
        </div>
        <div class="row">
            <label><input type="checkbox" id="s2" checked> стекло</label>
        </div>

        <div class="hint">
            <b>Управление:</b><br>
            • ЛКМ по пустому — вращать камеру<br>
            • ЛКМ по сфере — двигать сферу<br>
            • Колесо — зум<br>
        </div>
    </div>
</div>

<script>

const sub = (a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const add = (a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const mul = (a,s)=>[a[0]*s,a[1]*s,a[2]*s];
const dot = (a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross = (a,b)=>[a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const norm = a => { const l=Math.hypot(...a); return l<1e-12?[0,0,0]:[a[0]/l,a[1]/l,a[2]/l]; };


const spheres = [
    { center:[-2.5, 1.0, -7.0], radius:1.0, color:[0.8,0.1,0.1],
      type:'diffuse', specular:0.3, shininess:20, enabled:true },
    { center:[ 0.0, 1.5, -9.0], radius:1.5, color:[0.9,0.9,0.9],
      type:'reflective', reflectivity:0.85, specular:0.4, shininess:80, enabled:true },
    { center:[ 2.5, 1.0, -7.0], radius:1.0, color:[0.1,0.8,0.2],
      type:'transparent', transparency:0.9, refractiveIndex:1.5, specular:0.5, shininess:60, enabled:true },
];

let light = { position:[5, 8, -5], color:[1,1,1], intensity:1.0 };
const AMBIENT = [0.1, 0.1, 0.1];
const PLANE_Y = 0;

//камера
const cam = {
    target: [0, 1, -7],
    dist: 8,
    theta: 0,       // азимут
    phi: 0.15,      // наклон
};
function getCamPos() {
    const cp = Math.cos(cam.phi), sp = Math.sin(cam.phi);
    const ct = Math.cos(cam.theta), st = Math.sin(cam.theta);
    return [
        cam.target[0] + cam.dist * cp * st,
        cam.target[1] + cam.dist * sp,
        cam.target[2] + cam.dist * cp * ct,
    ];
}

function intersectSphere(o, d, s) {
    const oc = sub(o, s.center);
    const a = dot(d, d);
    const b = 2.0 * dot(oc, d);
    const c = dot(oc, oc) - s.radius * s.radius;
    const disc = b*b - 4*a*c;
    if (disc < 0) return null;
    const sq = Math.sqrt(disc);
    const t1 = (-b - sq) / (2*a);
    const t2 = (-b + sq) / (2*a);
    if (t1 > 0.001) return t1;
    if (t2 > 0.001) return t2;
    return null;
}
function intersectPlaneY(o, d, y) {
    if (Math.abs(d[1]) < 1e-6) return null;
    const t = (y - o[1]) / d[1];
    return t > 0.001 ? t : null;
}

function trace(o, d, depth) {
    if (depth > 4) return [0,0,0];

    let closestT = Infinity;
    let obj = null;
    let isPlane = false;

    for (const s of spheres) {
        if (!s.enabled) continue;
        const t = intersectSphere(o, d, s);
        if (t !== null && t < closestT) { closestT = t; obj = s; isPlane = false; }
    }
    const tp = intersectPlaneY(o, d, PLANE_Y);
    if (tp !== null && tp < closestT) { closestT = tp; obj = null; isPlane = true; }

    // Фон
    if (!obj && !isPlane) {
        const t = 0.5 * (d[1] + 1.0);
        return [0.5*(1-t)+0.3*t, 0.7*(1-t)+0.5*t, 1.0*(1-t)+0.8*t];
    }

    const hp = add(o, mul(d, closestT));
    let n, color, type_, refl=0, transp=0, ior=1.0, spec=0.5, shin=32;

    if (isPlane) {
        n = [0,1,0];
        const chk = (Math.floor(hp[0]) + Math.floor(hp[2])) % 2;
        color = chk === 0 ? [0.4,0.4,0.4] : [0.6,0.6,0.6];
        type_ = 'diffuse'; spec = 0.1; shin = 16;
    } else {
        n = norm(sub(hp, obj.center));
        color = obj.color; type_ = obj.type;
        refl = obj.reflectivity || 0;
        transp = obj.transparency || 0;
        ior = obj.refractiveIndex || 1.0;
        spec = obj.specular || 0.5;
        shin = obj.shininess || 32;
    }

    const inside = dot(d, n) > 0;
    if (inside) n = mul(n, -1);

    // Тень
    const L = light.position;
    const ld = norm(sub(L, hp));
    const ldist = Math.hypot(L[0]-hp[0], L[1]-hp[1], L[2]-hp[2]);
    let shadow = false;
    for (const s of spheres) {
        if (!s.enabled) continue;
        const t = intersectSphere(hp, ld, s);
        if (t !== null && t < ldist) { shadow = true; break; }
    }

    const local = [0,0,0];
    if (!shadow) {
        const diff = Math.max(0, dot(n, ld));
        const viewDir = norm(sub(getCamPos(), hp));
        const rd = sub(mul(n, 2*dot(n, ld)), ld);
        const sp = Math.pow(Math.max(0, dot(viewDir, rd)), shin);
        for (let c = 0; c < 3; c++) {
            local[c] = AMBIENT[c]*color[c] +
                       light.color[c]*light.intensity*(color[c]*diff + spec*sp);
        }
    } else {
        for (let c = 0; c < 3; c++) local[c] = AMBIENT[c]*color[c];
    }

    // Отражение
    let reflCol = [0,0,0];
    if ((type_ === 'reflective' || type_ === 'transparent') && depth < 4) {
        const rd = sub(d, mul(n, 2*dot(d, n)));
        reflCol = trace(hp, norm(rd), depth + 1);
    }

    // Преломление
    let refrCol = [0,0,0];
    if (type_ === 'transparent' && depth < 4) {
        const n1 = inside ? ior : 1.0;
        const n2 = inside ? 1.0 : ior;
        const eta = n1 / n2;
        const cosI = -dot(n, d);
        const sinT2 = eta*eta*(1 - cosI*cosI);
        if (sinT2 <= 1.0) {
            const cosT = Math.sqrt(1 - sinT2);
            const rdir = add(mul(d, eta), mul(n, eta*cosI - cosT));
            refrCol = trace(hp, norm(rdir), depth + 1);
        } else {
            refrCol = reflCol;
        }
    }

    const final = [0,0,0];
    for (let c = 0; c < 3; c++) {
        if (type_ === 'reflective') {
            final[c] = local[c]*(1-refl) + reflCol[c]*refl;
        } else if (type_ === 'transparent') {
            final[c] = local[c]*(1-transp) + refrCol[c]*transp;
        } else {
            final[c] = local[c];
        }
    }
    return final;
}


const canvas = document.getElementById('main');
const ctx = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;

// Offscreen canvas для рендера в низком разрешении
const off = document.createElement('canvas');
let RW = 200, RH = 150;
off.width = RW; off.height = RH;
const offCtx = off.getContext('2d');
let imgData = offCtx.createImageData(RW, RH);

function setRes(w, h) {
    RW = w; RH = h;
    off.width = RW; off.height = RH;
    imgData = offCtx.createImageData(RW, RH);
}

function screenRay(mx, my) {
    const camPos = getCamPos();
    const forward = norm(sub(cam.target, camPos));
    const right = norm(cross(forward, [0,1,0]));
    const up = cross(right, forward);

    const aspect = W / H;
    const fov = Math.tan(Math.PI / 4);
    const px = (2 * mx / W - 1) * aspect * fov;
    const py = (1 - 2 * my / H) * fov;

    const dir = norm(add(add(forward, mul(right, px)), mul(up, py)));
    return { origin: camPos, dir };
}

function render() {
    const camPos = getCamPos();
    const forward = norm(sub(cam.target, camPos));
    const right = norm(cross(forward, [0,1,0]));
    const up = cross(right, forward);

    const aspect = W / H;
    const fov = Math.tan(Math.PI / 4);
    const data = imgData.data;

    for (let y = 0; y < RH; y++) {
        for (let x = 0; x < RW; x++) {
            const px = (2 * (x + 0.5) / RW - 1) * aspect * fov;
            const py = (1 - 2 * (y + 0.5) / RH) * fov;
            const dir = norm(add(add(forward, mul(right, px)), mul(up, py)));
            const col = trace(camPos, dir, 0);
            const i = (y * RW + x) * 4;
            data[i]   = Math.min(255, Math.max(0, col[0] * 255));
            data[i+1] = Math.min(255, Math.max(0, col[1] * 255));
            data[i+2] = Math.min(255, Math.max(0, col[2] * 255));
            data[i+3] = 255;
        }
    }
    offCtx.putImageData(imgData, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(off, 0, 0, W, H);
}
//мышка
let dragging = null;     // 'orbit' | 'sphere'
let lastMouse = [0,0];
let dragOffset = [0,0,0];
let dragSphereIdx = -1;

function pickSphere(mx, my) {
    const ray = screenRay(mx, my);
    let best = -1, bestT = Infinity;
    for (let i = 0; i < spheres.length; i++) {
        if (!spheres[i].enabled) continue;
        const t = intersectSphere(ray.origin, ray.dir, spheres[i]);
        if (t !== null && t < bestT) { bestT = t; best = i; }
    }
    return best;
}

// Найти точку на горизонтальной плоскости y=Y, куда попал луч
function rayToPlaneY(mx, my, Y) {
    const ray = screenRay(mx, my);
    const t = intersectPlaneY(ray.origin, ray.dir, Y);
    if (t === null) return null;
    return add(ray.origin, mul(ray.dir, t));
}

canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (W / rect.width);
    const my = (e.clientY - rect.top)  * (H / rect.height);

    const idx = pickSphere(mx, my);
    if (idx >= 0 && e.button === 0) {
        dragging = 'sphere';
        dragSphereIdx = idx;
        const s = spheres[idx];
        const hit = rayToPlaneY(mx, my, s.center[1]);
        if (hit) {
            dragOffset = [s.center[0] - hit[0], 0, s.center[2] - hit[2]];
        } else {
            dragOffset = [0,0,0];
        }
        canvas.classList.add('dragging');
    } else {
        dragging = 'orbit';
        canvas.classList.add('dragging');
    }
    lastMouse = [e.clientX, e.clientY];
    setRes(160, 120);  // низкое разрешение при drag
    render();
});

canvas.addEventListener('mousemove', e => {
    if (!dragging) return;

    const dx = e.clientX - lastMouse[0];
    const dy = e.clientY - lastMouse[1];
    lastMouse = [e.clientX, e.clientY];

    if (dragging === 'orbit') {
        cam.theta -= dx * 0.008;
        cam.phi   += dy * 0.008;
        cam.phi = Math.max(-1.3, Math.min(1.3, cam.phi));
    } else if (dragging === 'sphere') {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left) * (W / rect.width);
        const my = (e.clientY - rect.top)  * (H / rect.height);
        const s = spheres[dragSphereIdx];
        const hit = rayToPlaneY(mx, my, s.center[1]);
        if (hit) {
            s.center[0] = hit[0] + dragOffset[0];
            s.center[2] = hit[2] + dragOffset[2];
        }
    }
    render();
});

window.addEventListener('mouseup', () => {
    if (dragging) {
        dragging = null;
        dragSphereIdx = -1;
        canvas.classList.remove('dragging');
        setRes(400, 300);  // высокое разрешение после drag
        render();
    }
});

canvas.addEventListener('wheel', e => {
    e.preventDefault();
    cam.dist *= (1 + Math.sign(e.deltaY) * 0.08);
    cam.dist = Math.max(3, Math.min(25, cam.dist));
    render();
}, { passive: false });


function bindSlider(id, valId, apply) {
    const el = document.getElementById(id);
    const vEl = document.getElementById(valId);
    const update = () => {
        vEl.textContent = parseFloat(el.value).toFixed(1);
        apply(parseFloat(el.value));
        render();
    };
    el.addEventListener('input', update);
    update();
}
bindSlider('lx', 'lxVal', v => light.position[0] = v);
bindSlider('ly', 'lyVal', v => light.position[1] = v);
bindSlider('lz', 'lzVal', v => light.position[2] = v);

['s0','s1','s2'].forEach((id, i) => {
    const el = document.getElementById(id);
    el.addEventListener('change', () => {
        spheres[i].enabled = el.checked;
        render();
    });
});


setRes(400, 300);
render();
setTimeout(render, 50);  // ещё раз для надёжности
</script>
</body>
</html>'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(404); self.end_headers(); return
        data = HTML_PAGE.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, fmt, *args): pass

if __name__ == '__main__':
    PORT = 8080
    for p in range(8080, 8090):
        try:
            server = ThreadingHTTPServer(('0.0.0.0', p), Handler)
            PORT = p
            break
        except OSError:
            continue
    url = f'http://localhost:{PORT}/'
    print("=" * 55)
    print(f"  ✅ СЕРВЕР ЗАПУЩЕН! Открой в браузере: {url}")
    print("  ⚠️  НЕ ЗАКРЫВАЙ ТЕРМИНАЛ!")
    print("  Остановка: Ctrl+C")
    print("=" * 55)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")