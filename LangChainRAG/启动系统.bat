@echo off
title LangChainRAG - one-click start

echo ==================================================
echo   LangChainRAG startup
echo   Keep this window open. Browser will open soon.
echo ==================================================
echo.

echo [1/3] Starting backend (port 8000) ...
start "backend 8000" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

echo [2/3] Starting frontend (port 5173) ...
start "frontend 5173" /D "%~dp0frontend" cmd /k "npm run dev"

echo [3/3] Waiting 8s, then opening browser...
timeout /t 8 /nobreak >nul

start http://localhost:5173

echo.
echo Done! Browser should open http://localhost:5173
echo If not, open it manually.
echo.
echo To stop: close windows "backend 8000" and "frontend 5173",
echo or press Ctrl+C inside them. You may close this window too.
echo.
pause
