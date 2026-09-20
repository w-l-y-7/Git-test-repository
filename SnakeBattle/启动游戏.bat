@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto noenv

echo.
echo   贪吃蛇对战  正在启动服务器...
echo.
echo   本机玩：浏览器打开  http://localhost:8000
echo   朋友玩：把下面那个 192.168 开头的地址发给他
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8000'"
ipconfig | findstr /i "IPv4"
echo.
echo   关掉这个黑窗口就是关掉服务器。
echo.

".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000

echo.
echo   服务器已停止。
pause
exit /b

:noenv
echo.
echo   找不到运行环境（.venv 文件夹）。
echo   请先双击「安装环境.bat」装一次，然后再启动。
echo.
pause
