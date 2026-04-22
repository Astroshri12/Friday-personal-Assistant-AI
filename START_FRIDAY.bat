@echo off
REM ═══════════════════════════════════════════════════════════════
REM  F.R.I.D.A.Y. v4.0 Launcher (Windows)
REM ═══════════════════════════════════════════════════════════════

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   F.R.I.D.A.Y. v4.0 — Power Mode    ║
echo   ╚══════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Download from: https://www.python.org/downloads/
    echo  During install, CHECK "Add Python to PATH"
    pause & exit /b 1
)
echo  Python detected.

echo  Checking/installing packages...
pip install fastapi uvicorn groq httpx python-dotenv pyautogui psutil Pillow -q
if errorlevel 1 (
    echo  ERROR: Failed to install packages.
    pause & exit /b 1
)
echo  All packages ready.

if not exist index.html (
    echo  ERROR: index.html not found in this folder!
    echo  Make sure server.py AND index.html are in the same folder.
    pause & exit /b 1
)

if not exist .env (
    echo  WARNING: .env file not found!
    echo  Create .env with:
    echo    GROQ_API_KEY=gsk_...
    echo    TAVILY_KEY=tvly-...
    echo    FRIDAY_SECRET=any_random_string
    pause & exit /b 1
)

echo.
echo  ══════════════════════════════════════════
echo   Starting F.R.I.D.A.Y. v4.0...
echo   Open browser: http://localhost:8000
echo   Press Ctrl+C to stop
echo  ══════════════════════════════════════════
echo.

python server.py

echo. & echo  Server stopped. & pause
