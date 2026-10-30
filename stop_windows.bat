@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   Arrêt de ScanFlow Pro V7...
echo ========================================
echo.

:: Arrêter les processus par titre de fenêtre
taskkill /FI "WINDOWTITLE eq *ScanFlow*" /F >nul 2>&1

:: Arrêter MongoDB
taskkill /FI "IMAGENAME eq mongod.exe" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] MongoDB arrêté
)

:: Arrêter les processus Node.js de ScanFlow
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" /NH') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Arrêter les processus Python de ScanFlow  
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /NH') do (
    netstat -ano | findstr ":8001" >nul 2>&1
    if %errorlevel% equ 0 (
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo [OK] Tous les services ont été arrêtés
echo.
timeout /t 2 >nul
