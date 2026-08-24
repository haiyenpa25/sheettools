@echo off
echo ========================================================
echo   SHEET CONVERTER — STARTING LOCAL DEV SERVERS
echo ========================================================
echo.
echo [1] Starting Vite Frontend Server (http://localhost:5173)...
start cmd /k "npm.cmd run dev"
echo.
echo [2] Starting PHP API Backend Server (http://localhost:8000)...
start cmd /k "D:\xampp\php\php.exe -S 127.0.0.1:8000 api.php"
echo.
echo ========================================================
echo   Both servers started! Open your browser at:
echo   http://localhost:5173
echo ========================================================
pause
