# AutoTasker 打包脚本
# 运行前确保已安装 pyinstaller: py -m pip install pyinstaller

Stop-Process -Name "AutoTasker" -Force -ErrorAction SilentlyContinue
Start-Sleep 1

py -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name "AutoTasker" `
    --paths src `
    --hidden-import win32gui `
    --hidden-import win32ui `
    --hidden-import win32api `
    --hidden-import win32con `
    --hidden-import win32com.client `
    --collect-submodules win32com `
    src/app.py

if ($LASTEXITCODE -eq 0) {
    Start-Process ".\dist\AutoTasker.exe"
    Write-Host "打包完成，已启动" -ForegroundColor Green
}

Write-Host ""
Write-Host "打包完成！EXE 文件在 dist\ 目录下。" -ForegroundColor Green
