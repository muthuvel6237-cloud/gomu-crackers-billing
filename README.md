# GOMU Crackers Billing Software

See the full handoff guide here:

- [SETUP_GUIDE.md](<C:\Users\Munees\Downloads\crackersbilling\gomu_crackers\SETUP_GUIDE.md>)

## Desktop App

### Run the desktop app directly

1. Install dependencies:
   `pip install -r requirements.txt`
2. Start the desktop application:
   `python desktop_app.py`

This launches Django with Waitress in the background and opens the billing system inside a native PyWebView window titled `Billing Software`.

### Build the Windows EXE

1. Install dependencies:
   `pip install -r requirements.txt`
2. Run the build script from the project root:
   `build.bat`

The build script:

- collects static files into `staticfiles/`
- packages templates, static assets, and `db.sqlite3`
- builds a single windowed EXE with PyInstaller
- applies an icon automatically if `app.ico` or `assets\app.ico` exists

### Final EXE output

PyInstaller writes the final desktop executable to:

`dist\BillingSoftware.exe`
