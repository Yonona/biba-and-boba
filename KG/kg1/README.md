## Сборка образа

```bash
docker build -t rotation-app-vnc .
```

## Запуск контейнера

```bash
docker run -it --rm -p 6080:6080 rotation-app-vnc
```

## Подключение

**Через браузер:** откройте http://localhost:6080/vnc.html и нажмите «Connect» (пар$

**Через VNC-клиент:** подключитесь к `localhost:5900`.

Приложение запустится внутри виртуального дисплея, и вы увидите его в окне VNC.
