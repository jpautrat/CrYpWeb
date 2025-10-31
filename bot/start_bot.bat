@echo off
REM Start script for Kraken Live Trading System
REM Starts the trading bot with proper environment setup

echo ========================================
echo Kraken Live Trading System - Starting
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: Configuration file (.env) not found!
    echo Please run configure.bat first to set up your configuration.
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import pandas, xgboost, lightgbm" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Required dependencies not installed
    echo Please run install.bat first
    pause
    exit /b 1
)

echo [1/3] Loading environment variables...
REM Load .env file and set environment variables
for /f "usebackq tokens=1,* delims==" %%a in ("%CD%\.env") do (
    set "%%a=%%b"
)

REM Check critical configuration
if "%LIVE_TRADING%"=="" set LIVE_TRADING=1
if "%LIVE_TRADING%"=="0" (
    echo ERROR: LIVE_TRADING must be set to 1 for live trading
    pause
    exit /b 1
)

if "%KRAKEN_KEY_1%"=="" (
    echo WARNING: No API keys found in configuration
    echo Please ensure you have configured at least one API key pair
    pause
)

echo.
echo [2/3] Starting trading bot...
echo.
echo WARNING: This will start LIVE TRADING with real funds!
echo Press Ctrl+C to stop the bot.
echo.
pause

REM Set Python path
set PYTHONPATH=%CD%

REM Start the bot
echo [3/3] Bot is running...
echo.
python main.py

REM If we get here, the bot has stopped
echo.
echo ========================================
echo Trading bot has stopped
echo ========================================
echo.
pause
