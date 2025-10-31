@echo off
REM ML Kraken Pro Live Trader - Startup Script
echo ============================================
echo ML Kraken Pro Live Trader - Starting
echo ============================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found
    echo Please run configure.bat first
    pause
    exit /b 1
)

REM Check if Python dependencies are installed
python -c "import xgboost" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Dependencies not installed
    echo Please run install.bat first
    pause
    exit /b 1
)

echo Starting trading bot...
echo Press Ctrl+C to stop
echo.

python bot\main.py

pause
