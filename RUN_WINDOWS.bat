@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo First follow the setup commands in README.md to create .venv and install requirements.
 pause
 exit /b 1
)
echo Open http://127.0.0.1:5000 in your browser after the server starts.
".venv\Scripts\python.exe" app.py
pause
