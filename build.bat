@echo off
setlocal

cd /d "%~dp0"

set "ICON_ARG="
if exist "app.ico" set "ICON_ARG=--icon app.ico"
if exist "assets\app.ico" set "ICON_ARG=--icon assets\app.ico"

python manage.py collectstatic --noinput
if errorlevel 1 exit /b %errorlevel%

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "BillingSoftware" ^
  %ICON_ARG% ^
  --add-data "billing_app\templates;billing_app\templates" ^
  --add-data "static;static" ^
  --add-data "staticfiles;staticfiles" ^
  --add-data "db.sqlite3;." ^
  --collect-all django ^
  --collect-all reportlab ^
  --collect-all webview ^
  --collect-submodules billing_app ^
  --collect-submodules gomu_crackers ^
  --hidden-import webview.platforms.edgechromium ^
  --hidden-import webview.platforms.winforms ^
  desktop_app.py
