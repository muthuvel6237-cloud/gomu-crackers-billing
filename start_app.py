import os
import subprocess
import sys
import webbrowser
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

subprocess.Popen([
    sys.executable,
    "manage.py",
    "runserver",
    "127.0.0.1:8000"
])

time.sleep(3)

webbrowser.open("http://127.0.0.1:8000/billing/")
