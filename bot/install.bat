@echo off
REM Install script for Kraken Live Trading System
REM Installs all Python dependencies and sets up the environment

echo ========================================
echo Kraken Live Trading System - Installer
echo ========================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from python.org
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'; print('Python version OK')"
if errorlevel 1 (
    echo ERROR: Python 3.10 or higher is required
    pause
    exit /b 1
)

echo.
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/4] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [4/4] Creating directories...
if not exist "data\raw" mkdir data\raw
if not exist "data\features" mkdir data\features
if not exist "models" mkdir models
if not exist "logs" mkdir logs

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Run configure.bat to set up your API keys and settings
echo 2. Review the configuration carefully
echo 3. Run start_bot.bat to start trading
echo.
pause
