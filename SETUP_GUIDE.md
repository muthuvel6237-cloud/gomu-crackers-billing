# Billing Software Setup Guide

This guide is for running, testing, and building the Django billing project as a Windows desktop application.

## Project Stack

- Django backend
- Django templates frontend
- SQLite database
- PyWebView desktop window
- Waitress production server
- PyInstaller EXE build

## What This Project Does

The project runs Django in the background using Waitress and opens the app inside a native Windows desktop window using PyWebView.

The user does not need to:

- open a browser
- type `localhost`
- install Python on the final client system after EXE build

## Requirements For Development

Install these on the developer machine:

- Python 3.12 or 3.13
- `pip`
- Windows OS

## Install Project Dependencies

Open terminal in the project folder and run:

```bat
pip install -r requirements.txt
```

## How To Run The Project In Desktop Mode

Run this from the project root:

```bat
python desktop_app.py
```

What happens:

- Django starts with Waitress in the background
- a PyWebView desktop window opens
- the app loads inside the native window

## How To Run The Project In Normal Django Mode

If needed for debugging:

```bat
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## How To Build The EXE

From the project root, run:

```bat
build.bat
```

This build script will:

- collect static files
- include templates
- include static files
- include the SQLite database
- build a single `.exe`
- hide the console window

## Where The EXE Will Be Generated

After successful build, the output file will be here:

```text
dist\BillingSoftware.exe
```

## How The Database Works In The EXE

The starter database file is packaged from:

```text
db.sqlite3
```

When the EXE runs on a Windows machine, the database is copied on first launch to:

```text
%LOCALAPPDATA%\Billing Software\db.sqlite3
```

That means:

- SQLite does not need to be installed separately
- Python does not need to be installed on the client machine
- Django does not need to be installed on the client machine

## Possible Client System Dependency

Some Windows systems may need Microsoft WebView2 Runtime for PyWebView.

Usually:

- Windows 10 and Windows 11 already have it
- no manual install is needed on most systems

If the app window does not open properly on another PC, check WebView2 Runtime first.

## How To Change The App Icon

The build script already supports icon files automatically.

You can use either of these paths:

- `app.ico`
- `assets\app.ico`

## Icon Change Steps

1. Prepare a Windows `.ico` file.
2. Put it in the project root as `app.ico`.
3. Or put it inside `assets` as `assets\app.ico`.
4. Run `build.bat` again.
5. The new EXE will be built with that icon.

## Important Notes About Icons

- The icon file must be `.ico`, not `.png` or `.jpg`
- If Windows still shows the old icon, rebuild and refresh Explorer
- Sometimes Windows icon cache causes delay in showing the new icon

## How To Send The App To Another Person

For a basic handoff, send:

- `dist\BillingSoftware.exe`

That is enough for most systems.

## If You Want To Send Existing Billing Data Also

If you want the other person to receive the current working data too, then also send the database file from the machine where the EXE has already been used:

```text
%LOCALAPPDATA%\Billing Software\db.sqlite3
```

Without that file, the EXE will start with the bundled starter database.

## Recommended Handoff Steps For Junior Developer

1. Install Python.
2. Run `pip install -r requirements.txt`
3. Run `python desktop_app.py`
4. Confirm the desktop window opens correctly.
5. Add `app.ico` if custom icon is needed.
6. Run `build.bat`
7. Test `dist\BillingSoftware.exe`

## Main Files Used For Desktop Build

- `desktop_app.py`
- `build.bat`
- `requirements.txt`
- `gomu_crackers\settings.py`
- `gomu_crackers\runtime_paths.py`

## Quick Commands

Install dependencies:

```bat
pip install -r requirements.txt
```

Run desktop app:

```bat
python desktop_app.py
```

Build EXE:

```bat
build.bat
```
