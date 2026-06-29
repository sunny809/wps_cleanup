@echo off
chcp 65001 >nul
title WPS 清理工具 - 本地构建脚本

echo ========================================
echo   WPS 磁盘清理工具 - 本地构建
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/5] 安装构建依赖...
pip install pyinstaller

:: 生成图标
echo [2/5] 生成应用图标...
python scripts/generate_icon.py
if %errorlevel% neq 0 (
    echo [警告] 图标生成失败，将继续使用默认图标
)

:: 清理旧构建
echo [3/5] 清理旧构建...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: PyInstaller 打包
echo [4/5] 正在打包为 EXE...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "WPS-Cleanup" ^
    --icon "assets/icon.ico" ^
    --add-data "wps_cleanup;wps_cleanup" ^
    --noconfirm ^
    --clean ^
    main.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: 复制说明文件
echo [5/5] 复制说明文件...
copy README.md dist\ >nul

echo.
echo ========================================
echo   ✅ 构建完成！
echo.
echo   输出文件: dist\WPS-Cleanup.exe
echo   大小: %~z0 bytes
echo ========================================
echo.
pause
