#!/bin/bash
# Запускаем виртуальный дисплей Xvfb на :99
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99

# Запускаем x11vnc для трансляции X-дисплея в VNC
x11vnc -display :99 -forever -nopw -shared -bg

# Запускаем websockify для доступа через браузер (novnc)
websockify --web /usr/share/novnc 6080 localhost:5900 &

# Запускаем само приложение
python rotation_3d.py
