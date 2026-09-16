FROM python:3.9-slim

# Устанавливаем системные зависимости: tkinter, Xvfb, x11vnc, novnc (для веб-доступа)
RUN apt-get update && apt-get install -y \
    tk \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rotation_3d.py .

# Скрипт запуска: стартуем Xvfb, затем VNC и приложение
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 6080 5900

CMD ["./start.sh"]
