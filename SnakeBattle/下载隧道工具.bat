@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto noenv

".venv\Scripts\python.exe" get_cloudflared.py
pause
exit /b

:noenv
echo.
echo   找不到运行环境。请先双击「安装环境.bat」装一次。
echo.
pause
