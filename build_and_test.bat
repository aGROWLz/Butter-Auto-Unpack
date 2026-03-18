@echo off
REM Build and Test Script for Butter Auto Unpack
REM Butter自动解压构建和测试脚本

echo ============================================================
echo Butter Auto Unpack 构建和测试
echo ============================================================
echo.

REM 检查PyInstaller是否安装
echo [1/5] 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] PyInstaller未安装
    echo 请运行: pip install pyinstaller
    exit /b 1
)
echo [成功] PyInstaller已安装
echo.

REM 清理旧的构建文件
echo [2/5] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo [成功] 清理完成
echo.

REM 运行PyInstaller构建
echo [3/5] 运行PyInstaller构建...
pyinstaller Butter-Auto-Unpack.spec --clean
if errorlevel 1 (
    echo [错误] 构建失败
    exit /b 1
)
echo [成功] 构建完成
echo.

REM 运行基本测试
echo [4/5] 运行基本测试...
python test_packaged_app.py
if errorlevel 1 (
    echo [错误] 基本测试失败
    exit /b 1
)
echo [成功] 基本测试通过
echo.

REM 运行7z可用性测试
echo [5/5] 运行7z可用性测试...
python test_7z_availability.py
if errorlevel 1 (
    echo [错误] 7z可用性测试失败
    exit /b 1
)
echo [成功] 7z可用性测试通过
echo.

REM 显示构建结果
echo ============================================================
echo 构建成功！
echo ============================================================
echo.
echo 可执行文件位置: dist\Butter-Auto-Unpack.exe
echo 文件大小:
dir dist\Butter-Auto-Unpack.exe | find "Butter-Auto-Unpack.exe"
echo.
echo 要运行应用程序，请执行:
echo   dist\Butter-Auto-Unpack.exe
echo.
echo 要查看调试信息，请执行:
echo   dist\Butter-Auto-Unpack.exe --debug
echo.

exit /b 0
