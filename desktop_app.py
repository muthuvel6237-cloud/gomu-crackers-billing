import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

import webview
from waitress.server import create_server

# Enable file downloads (PDF bills, Excel exports, DB backups)
webview.settings['ALLOW_DOWNLOADS'] = True

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gomu_crackers.settings")

import django  # noqa: E402


SERVER = None


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def create_app_server(application, host: str = "127.0.0.1") -> tuple:
    for attempt in range(10):
        try:
            port = find_free_port()
            server = create_server(application, host=host, port=port, threads=8)
            return server, port
        except Exception:
            time.sleep(0.1)

    # Fallback to port 0 (OS picks available port)
    server = create_server(application, host=host, port=0, threads=8)
    return server, server.effective_port


def prepare_runtime_assets() -> None:
    django.setup()

    from django.conf import settings
    from django.core.management import call_command

    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists() or not any(static_root.iterdir()):
        try:
            call_command("collectstatic", interactive=False, verbosity=0)
        except Exception:
            pass
    try:
        call_command("migrate", interactive=False, verbosity=0)
    except Exception:
        pass


def wait_for_server(url: str, server_thread: threading.Thread, timeout: int = 45) -> None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        if not server_thread.is_alive():
            raise RuntimeError(f"Server thread terminated unexpectedly while waiting for {url}")

        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.2)

    raise RuntimeError(f"Timed out while waiting for the application server at {url}")


def stop_waitress_server(*_args) -> None:
    global SERVER

    if SERVER is not None:
        SERVER.close()
        SERVER = None


def main() -> None:
    global SERVER

    prepare_runtime_assets()

    host = "127.0.0.1"
    from gomu_crackers.wsgi import application

    SERVER, port = create_app_server(application, host=host)
    url = f"http://{host}:{port}/billing/"

    server_thread = threading.Thread(
        target=SERVER.run,
        daemon=True,
        name="waitress-server",
    )
    server_thread.start()

    wait_for_server(url, server_thread)

    window = webview.create_window(
        "Billing Software",
        url,
        width=1440,
        height=900,
        min_size=(1100, 720),
        resizable=True,
    )
    window.events.closed += stop_waitress_server
    webview.start(debug=False)


if __name__ == "__main__":
    main()
