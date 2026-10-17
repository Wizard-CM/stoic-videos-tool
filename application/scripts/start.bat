@echo off
REM ToonForge dev server launcher (Windows)
REM Builds frontend if needed, starts backend API, and opens the browser.

setlocal enabledelayedexpansion
cd /d "%~dp0\.."
set REPO_ROOT=%cd%
set FRONTEND_DIR=%REPO_ROOT%\frontend
set BACKEND_DIR=%REPO_ROOT%\backend
set FRONTEND_DIST=%FRONTEND_DIR%\dist

echo Starting ToonForge dev servers...

REM Build frontend if dist doesn't exist
if not exist "%FRONTEND_DIST%" (
    echo Building frontend...
    cd /d "%FRONTEND_DIR%"
    call npm run build
    if errorlevel 1 (
        echo Frontend build failed.
        exit /b 1
    )
)

REM Start backend API
echo Starting API server on http://127.0.0.1:8000
cd /d "%BACKEND_DIR%"
start cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

REM Wait a moment and open browser
timeout /t 2 /nobreak
start http://127.0.0.1:8000

echo Dev servers started. Check the opened browser window.
