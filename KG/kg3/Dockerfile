FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-tk \
        xvfb \
        x11vnc \
        novnc \
        websockify \
        procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app ./app
COPY tests ./tests
COPY requirements.txt .

EXPOSE 6080 5900

CMD ["bash", "-lc", "Xvfb :99 -screen 0 1280x800x24 -ac -noreset >/tmp/xvfb.log 2>&1 & \\\n    sleep 1; \\\n    x11vnc -display :99 -forever -shared -rfbport 5900 -nopw >/tmp/x11vnc.log 2>&1 & \\\n    websockify --web /usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 & \\\n    sleep 1; \\\n    python3 app/main.py"]
