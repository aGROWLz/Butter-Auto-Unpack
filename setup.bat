@echo off
echo ========================================
echo Auto Unpack Manager - Setup Script
echo ========================================
echo.

echo Step 1: Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo Virtual environment created successfully.
echo.

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated.
echo.

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 4: Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

echo Step 5: Checking 7z tools...
if exist "resources\7za.exe" (
    echo 7za.exe found in resources directory.
) else (
    echo WARNING: 7za.exe not found in resources directory.
    echo Please place 7za.exe in the resources folder.
)
echo.

echo Step 6: Creating config file...
if not exist "config.json" (
    copy config.template.json config.json
    echo config.json created from template.
    echo Please edit config.json to set your target and unpack folders.
) else (
    echo config.json already exists.
)
echo.

echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To run the application:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python main.py
echo.
pause
