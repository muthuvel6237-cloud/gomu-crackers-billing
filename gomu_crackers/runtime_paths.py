import os
import shutil
import sys
from pathlib import Path


APP_NAME = "Billing Software"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return project_root()


def app_data_root() -> Path:
    if is_frozen():
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        target = local_app_data / APP_NAME
    else:
        target = project_root()

    target.mkdir(parents=True, exist_ok=True)
    return target


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def writable_path(*parts: str) -> Path:
    target = app_data_root().joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def ensure_file(resource_name: str) -> Path:
    destination = writable_path(resource_name)
    source = resource_path(resource_name)

    if not destination.exists() and source.exists():
        shutil.copy2(source, destination)

    return destination


def ensure_directory(resource_name: str) -> Path:
    destination = writable_path(resource_name)
    source = resource_path(resource_name)

    if source.exists() and not destination.exists():
        shutil.copytree(source, destination)
    else:
        destination.mkdir(parents=True, exist_ok=True)

    return destination
