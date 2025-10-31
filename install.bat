@echo off
REM ML Kraken Pro Live Trader - Installation Script
REM This script installs all dependencies for the trading system

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - INSTALLATION
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/5] Installing required packages...
echo This may take several minutes...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo [4/5] Creating necessary directories...
if not exist "data" mkdir data
if not exist "data\raw" mkdir data\raw
if not exist "data\features" mkdir data\features
if not exist "data\models" mkdir data\models
if not exist "data\logs" mkdir data\logs
if not exist "data\logs\audit" mkdir data\logs\audit

echo.
echo [5/5] Creating configuration file...
if not exist ".env" (
    copy .env.example .env
    echo Configuration file created: .env
    echo.
    echo IMPORTANT: You MUST edit .env and add your Kraken API keys!
    echo Open .env in a text editor and fill in all required values.
) else (
    echo Configuration file already exists (.env)
)

echo.
echo ================================================================================
echo INSTALLATION COMPLETE
echo ================================================================================
echo.
echo NEXT STEPS:
echo 1. Edit .env file and add your 5 Kraken API keys
echo 2. Review and adjust configuration parameters in .env
echo 3. Run configure.bat to validate your configuration
echo 4. Run start_bot.bat to start the trading system
echo.
echo WARNING: This is a LIVE TRADING system that uses REAL MONEY
echo Make sure you understand the risks before starting the bot
echo ================================================================================
echo.
pause
