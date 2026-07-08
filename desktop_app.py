import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

import webview
from waitress.server import create_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gomu_crackers.settings")

import django  # noqa: E402


SERVER = None


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def prepare_runtime_assets() -> None:
    django.setup()

    from django.conf import settings
    from django.core.management import call_command

    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists() or not any(static_root.iterdir()):
        call_command("collectstatic", interactive=False, verbosity=0)


def wait_for_server(url: str, timeout: int = 30) -> None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.25)

    raise RuntimeError(f"Timed out while waiting for the application server at {url}")


def start_waitress_server(host: str, port: int) -> None:
    global SERVER

    from gomu_crackers.wsgi import application

    SERVER = create_server(application, host=host, port=port, threads=8)
    SERVER.run()


def stop_waitress_server(*_args) -> None:
    global SERVER

    if SERVER is not None:
        SERVER.close()
        SERVER = None


def main() -> None:
    prepare_runtime_assets()

    host = "127.0.0.1"
    port = find_free_port()
    url = f"http://{host}:{port}/billing/"

    server_thread = threading.Thread(
        target=start_waitress_server,
        args=(host, port),
        daemon=True,
        name="waitress-server",
    )
    server_thread.start()

    wait_for_server(url)

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
