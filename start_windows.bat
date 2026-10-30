@echo off
chcp 65001 >nul
cls

:: عرض شعار التطبيق
echo.
echo     ███████╗ ██████╗ █████╗ ███╗   ██╗███████╗██╗      ██████╗ ██╗    ██╗
echo     ██╔════╝██╔════╝██╔══██╗████╗  ██║██╔════╝██║     ██╔═══██╗██║    ██║
echo     ███████╗██║     ███████║██╔██╗ ██║█████╗  ██║     ██║   ██║██║ █╗ ██║
echo     ╚════██║██║     ██╔══██║██║╚██╗██║██╔══╝  ██║     ██║   ██║██║███╗██║
echo     ███████║╚██████╗██║  ██║██║ ╚████║██║     ███████╗╚██████╔╝╚███╔███╔╝
echo     ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝
echo.
echo                        Pro V7 - Enterprise Edition
echo                   Système intelligent de traitement PDF
echo.
echo ================================================================================
echo.

title ScanFlow Pro V7 - Démarrage...

:: Créer le dossier de données MongoDB si nécessaire
if not exist "data\db" (
    echo Création du répertoire de données MongoDB...
    mkdir data\db
)

:: Vérifier si MongoDB est déjà en cours d'exécution
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I /N "mongod.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MongoDB est déjà en cours d'exécution
) else (
    echo [1/3] Démarrage de MongoDB...
    start "MongoDB - ScanFlow" /MIN mongod --dbpath="%CD%\data\db" --bind_ip_all --port 27017
    timeout /t 3 >nul
    echo [OK] MongoDB démarré
)

:: Démarrer Backend
echo [2/3] Démarrage du Backend (FastAPI)...
cd backend
start "Backend - ScanFlow" /MIN cmd /c "python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 5 >nul
echo [OK] Backend démarré sur http://localhost:8001
cd ..

:: Démarrer Frontend
echo [3/3] Démarrage du Frontend (React)...
cd frontend
start "Frontend - ScanFlow" /MIN cmd /c "set BROWSER=none && yarn start"
timeout /t 8 >nul
echo [OK] Frontend démarré sur http://localhost:3000
cd ..

:: Ouvrir le navigateur
echo.
echo ================================================================================
echo.
echo               ✓ ScanFlow Pro V7 est maintenant actif!
echo.
echo     Interface Web:  http://localhost:3000
echo     API Backend:    http://localhost:8001
echo     Documentation:  http://localhost:8001/docs
echo.
echo ================================================================================
echo.
echo Ouverture du navigateur dans 3 secondes...
timeout /t 3 >nul
start http://localhost:3000

echo.
echo L'application est en cours d'exécution en arrière-plan.
echo.
echo Pour arrêter l'application, exécutez: stop_windows.bat
echo Ou fermez simplement cette fenêtre.
echo.
pause

:: Arrêter tous les processus si l'utilisateur appuie sur une touche
echo.
echo Arrêt de l'application...
call stop_windows.bat
