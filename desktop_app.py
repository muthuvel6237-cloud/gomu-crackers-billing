import os
import socket
import threading
import time
from pathlib import Path

import webview
from waitress.server import create_server

# Enable file downloads (PDF bills, Excel exports, DB backups)
webview.settings['ALLOW_DOWNLOADS'] = True

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gomu_crackers.settings")

import django  # noqa: E402


SERVER = None


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


def wait_for_server(host: str, port: int, server_thread: threading.Thread, timeout: int = 15) -> None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        if not server_thread.is_alive():
            raise RuntimeError(f"Server thread terminated unexpectedly while starting on port {port}")

        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)

    raise RuntimeError(f"Timed out waiting for application server to open on {host}:{port}")


def stop_waitress_server(*_args) -> None:
    global SERVER

    if SERVER is not None:
        try:
            SERVER.close()
        except Exception:
            pass
        SERVER = None


def main() -> None:
    global SERVER

    prepare_runtime_assets()

    host = "127.0.0.1"
    from gomu_crackers.wsgi import application

    # Let the OS kernel assign a guaranteed available free port atomically
    SERVER = create_server(application, host=host, port=0, threads=8)
    port = int(SERVER.effective_port)
    url = f"http://{host}:{port}/billing/"

    server_thread = threading.Thread(
        target=SERVER.run,
        daemon=True,
        name="waitress-server",
    )
    server_thread.start()

    wait_for_server(host, port, server_thread, timeout=15)

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
