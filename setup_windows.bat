@echo off
chcp 65001 >nul
echo ========================================
echo     ScanFlow Pro V7 - Installation
echo ========================================
echo.

:: التحقق من Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installé!
    echo Téléchargez Python 3.11+ depuis: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python trouvé

:: التحقق من Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Node.js n'est pas installé!
    echo Téléchargez Node.js depuis: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js trouvé

:: التحقق من MongoDB
where mongod >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] MongoDB n'est pas installé!
    echo Téléchargez MongoDB Community depuis: https://www.mongodb.com/try/download/community
    pause
    exit /b 1
)
echo [OK] MongoDB trouvé

:: التحقق من Tesseract
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo [ATTENTION] Tesseract OCR n'est pas installé!
    echo Installation recommandée depuis: https://github.com/UB-Mannheim/tesseract/wiki
    echo Le programme continuera mais l'OCR ne fonctionnera pas.
    timeout /t 3 >nul
)

echo.
echo ========================================
echo     Installation des dépendances
echo ========================================
echo.

:: Backend
echo [1/2] Installation des dépendances Backend...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERREUR] Installation Backend échouée!
    pause
    exit /b 1
)
echo [OK] Backend installé
cd ..

:: Frontend  
echo [2/2] Installation des dépendances Frontend...
cd frontend
call yarn install
if %errorlevel% neq 0 (
    echo [ERREUR] Installation Frontend échouée!
    pause
    exit /b 1
)
echo [OK] Frontend installé
cd ..

echo.
echo ========================================
echo     Installation terminée avec succès!
echo ========================================
echo.
echo Utilisez "start_windows.bat" pour démarrer l'application.
echo.
pause
