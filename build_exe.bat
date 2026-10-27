@echo off
cd /d "%~dp0"
echo Collecting static assets...
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
echo Building Executable with PyInstaller...
.\.venv\Scripts\python.exe -m PyInstaller BillingSoftware.spec --noconfirm
echo Copying to Desktop...
copy /Y "dist\BillingSoftware.exe" "%USERPROFILE%\Desktop\Gomu_Crackers_Billing_Updated.exe"
echo Done! Updated EXE is ready on your Desktop.
pause
