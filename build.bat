@echo off
chcp 65001 >nul
echo ====================================
echo  AutoTasker - Build EXE
echo ====================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 关闭正在运行的 AutoTasker
echo [1/4] 关闭运行中的 AutoTasker...
taskkill /F /IM AutoTasker.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: 检查 Python 是否可用
echo [2/4] 检查环境...
py --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确认已安装 Python 并添加到 PATH
    pause
    exit /b 1
)

:: 检查 PyInstaller 是否安装
py -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 PyInstaller...
    py -m pip install pyinstaller PyQt6 apscheduler
)

:: 执行打包
echo [3/4] 正在打包...
py -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "AutoTasker" ^
    --icon "assets\logo.ico" ^
    --paths src ^
    --add-data "assets;assets" ^
    src\app.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

:: 打包成功，启动新版本
echo [4/4] 打包完成，正在启动...
start "" "dist\AutoTasker.exe"

echo.
echo ====================================
echo  打包成功！文件位置：
echo  %~dp0dist\AutoTasker.exe
echo ====================================
echo.
pause
