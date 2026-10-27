@echo off
cd /d "%~dp0"
echo Starting Gomu Crackers Billing Server...
echo Open your browser at http://127.0.0.1:8000/billing/
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
