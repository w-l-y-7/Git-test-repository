@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto noenv
if not exist "cloudflared.exe" goto nocf

".venv\Scripts\python.exe" start_public.py
pause
exit /b

:noenv
echo.
echo   找不到运行环境。请先双击「安装环境.bat」装一次。
echo.
pause
exit /b

:nocf
echo.
echo   找不到 cloudflared.exe（隧道工具）。
echo   请先双击「下载隧道工具.bat」，下载完再启动。
echo.
pause
