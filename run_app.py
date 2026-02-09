"""
Единая точка входа: запускает API и веб-интерфейс автоматически.

Просто запустите этот файл двойным кликом или через:
    python run_app.py

Скрипт автоматически:
1. Запускает API (FastAPI) на порту 8000
2. Запускает HTTP-сервер для веб-интерфейса на порту 8080
3. Открывает браузер с веб-интерфейсом
4. Всё работает до закрытия окна (Ctrl+C)
"""

from __future__ import annotations

import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any


# Порты
API_PORT = 8000
WEB_PORT = 8080


def get_runtime_root() -> Path:
    """
    Вернуть каталог с runtime-файлами приложения.

    - Обычный запуск: папка с run_app.py
    - PyInstaller onefile: sys._MEIPASS
    - PyInstaller onedir: папка с exe
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP обработчик с поддержкой CORS для веб-интерфейса."""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Отключаем логирование каждого запроса для чистоты консоли
        pass


def start_web_server(project_root: Path, port: int) -> socketserver.TCPServer:
    """Запустить HTTP-сервер для раздачи HTML файла."""
    os.chdir(str(project_root))
    handler = CustomHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    def serve():
        print(f"Веб-сервер запущен на http://localhost:{port}")
        httpd.serve_forever()
    
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return httpd


def start_api_server(project_root: Path) -> tuple[str, Any]:
    """
    Запустить API-сервер.

    Возвращает:
      ("subprocess", process) для обычного запуска
      ("embedded", (server, thread)) для frozen-режима (exe)
    """
    # В собранном exe нельзя запускать web_api.py как отдельный скрипт.
    # Поэтому поднимаем FastAPI внутри отдельного потока.
    if getattr(sys, "frozen", False):
        import uvicorn
        from web_api import app

        print(f"Запуск API на порту {API_PORT} (embedded)...")
        config = uvicorn.Config(app, host="127.0.0.1", port=API_PORT, log_level="info")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        return "embedded", (server, thread)

    python_exe = sys.executable
    api_script = project_root / "web_api.py"
    
    if not api_script.exists():
        raise FileNotFoundError(f"Файл {api_script} не найден")
    
    print(f"Запуск API на порту {API_PORT}...")
    # Важно: не прячем вывод. Если зависимостей нет/ошибка импорта — пользователь сразу увидит.
    process = subprocess.Popen(
        [python_exe, str(api_script)],
        cwd=str(project_root),
    )
    return "subprocess", process


def wait_for_api(api_mode: str, api_handle: Any, port: int, timeout_s: int = 30) -> bool:
    """
    Подождать, пока API станет доступен.

    Если процесс API завершился раньше — сразу возвращаем False.
    """
    import socket

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # Если API-носитель уже умер — не ждём дальше
        if api_mode == "subprocess":
            if api_handle.poll() is not None:
                return False
        else:
            _, api_thread = api_handle
            if not api_thread.is_alive():
                return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass

        time.sleep(0.5)

    return False


def main() -> None:
    project_root = get_runtime_root()
    
    print("=" * 60)
    print("🚀 Запуск калькулятора патч-кордов")
    print("=" * 60)
    
    # Запускаем API
    try:
        api_mode, api_handle = start_api_server(project_root)
    except Exception as e:
        print(f"❌ Ошибка запуска API: {e}")
        sys.exit(1)
    
    # Ждём, пока API поднимется
    print(f"⏳ Ожидание запуска API...")
    if not wait_for_api(api_mode, api_handle, API_PORT):
        # Если процесс завершился — дадим более понятную подсказку
        if api_mode == "subprocess" and api_handle.poll() is not None:
            print("❌ API завершился сразу после запуска.")
        else:
            print("❌ API не запустился за отведённое время.")

        print("")
        print("Подсказка: чаще всего это происходит, если не установлены зависимости.")
        print("Установите их один раз командой:")
        print("  pip install -r requirements.txt")
        print("")
        if api_mode == "subprocess":
            api_handle.terminate()
        else:
            api_server, api_thread = api_handle
            api_server.should_exit = True
            api_thread.join(timeout=5)
        sys.exit(1)
    
    print(f"✅ API запущен на http://localhost:{API_PORT}")
    
    # Запускаем веб-сервер
    try:
        web_server = start_web_server(project_root, WEB_PORT)
    except Exception as e:
        print(f"❌ Ошибка запуска веб-сервера: {e}")
        if api_mode == "subprocess":
            api_handle.terminate()
        else:
            api_server, api_thread = api_handle
            api_server.should_exit = True
            api_thread.join(timeout=5)
        sys.exit(1)
    
    # Открываем браузер (используем новую версию фронтенда)
    web_url = f"http://localhost:{WEB_PORT}/web_interface_v2.html"
    print(f"🌐 Открываю веб-интерфейс: {web_url}")
    time.sleep(0.5)  # Небольшая задержка перед открытием браузера
    webbrowser.open(web_url)
    
    print("=" * 60)
    print("✅ Всё готово! Веб-интерфейс открыт в браузере.")
    print("   Нажмите Ctrl+C для остановки серверов.")
    print("=" * 60)
    
    try:
        # Держим процессы запущенными
        if api_mode == "subprocess":
            api_handle.wait()
        else:
            _, api_thread = api_handle
            while api_thread.is_alive():
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка серверов...")
        web_server.shutdown()
        if api_mode == "subprocess":
            api_handle.terminate()
            try:
                api_handle.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_handle.kill()
        else:
            api_server, api_thread = api_handle
            api_server.should_exit = True
            api_thread.join(timeout=5)
        print("✅ Серверы остановлены")


if __name__ == "__main__":
    main()

