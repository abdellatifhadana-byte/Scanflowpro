@echo off
title ScanFlow Pro V7 Startup
color 0A

echo ===============================================
echo    ScanFlow Pro V7 - Enterprise Edition
echo ===============================================
echo.

REM Check Python
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11 or higher from python.org
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Node.js
echo [2/6] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed!
    echo Please install Node.js from nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found

REM Check Tesseract
echo [3/6] Checking Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Tesseract not found in PATH
    echo Attempting to install via Chocolatey...
    choco install tesseract -y
    if errorlevel 1 (
        echo [ERROR] Failed to install Tesseract
        echo Please download manually from: https://github.com/UB-Mannheim/tesseract/wiki
        pause
    )
) else (
    echo [OK] Tesseract found
)

REM Setup Backend
echo [4/6] Setting up Backend...
cd /d "%~dp0backend"

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python packages...
pip install -r requirements.txt --quiet

REM Setup Frontend
echo [5/6] Setting up Frontend...
cd /d "%~dp0frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing Node packages...
    call yarn install
) else (
    echo [OK] Node modules already installed
)

REM Start Services
echo [6/6] Starting services...
echo.
echo ===============================================
echo    Services are starting...
echo ===============================================
echo.

REM Start Backend
cd /d "%~dp0backend"
start "ScanFlow Backend" cmd /k "venv\Scripts\activate.bat && python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start Frontend
cd /d "%~dp0frontend"
start "ScanFlow Frontend" cmd /k "yarn start"

echo.
echo ===============================================
echo    ScanFlow Pro V7 is starting!
echo ===============================================
echo.
echo Backend: http://localhost:8001
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >nul

REM Stop services
taskkill /FI "WINDOWTITLE eq ScanFlow*" /F
echo Services stopped.
