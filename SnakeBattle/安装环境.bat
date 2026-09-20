@echo off
cd /d "%~dp0"

echo.
echo   首次使用：正在安装运行环境，大约需要一分钟...
echo.

where py >nul 2>nul
if %errorlevel%==0 goto usepy
set "PY=python"
goto makeenv

:usepy
set "PY=py"

:makeenv
%PY% -m venv .venv

if not exist ".venv\Scripts\python.exe" goto failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo   装好了。以后直接双击「启动游戏.bat」就行。
echo.
pause
exit /b

:failed
echo.
echo   建环境失败。请确认电脑上装了 Python 3.10 或更高版本。
echo.
pause
