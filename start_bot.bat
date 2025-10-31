@echo off
REM ML Kraken Pro Live Trader - Start Script
REM This script starts the live trading system

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - STARTING
echo ================================================================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: Configuration file (.env) not found
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Final safety warning
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                            ⚠️  CRITICAL WARNING ⚠️                          ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║  This is a LIVE TRADING system that will:                                 ║
echo ║  • Place REAL ORDERS on Kraken exchange                                   ║
echo ║  • Use REAL MONEY from your account                                       ║
echo ║  • Execute trades automatically based on ML models                        ║
echo ║                                                                            ║
echo ║  Before proceeding, ensure:                                               ║
echo ║  ✓ You have configured .env with valid API keys                           ║
echo ║  ✓ You understand the risks of algorithmic trading                        ║
echo ║  ✓ You have tested the system with small capital first                    ║
echo ║  ✓ You are ready to monitor the system actively                           ║
echo ║                                                                            ║
echo ║  EMERGENCY CONTROLS:                                                      ║
echo ║  • Press Ctrl+C to stop the bot gracefully                                ║
echo ║  • Create file "data/.kill_switch" to emergency halt                      ║
echo ║  • Use kill switch password from .env for immediate stop                  ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

set /p confirm="Type 'START' (in capitals) to begin live trading: "

if not "%confirm%"=="START" (
    echo.
    echo Bot startup canceled.
    echo.
    pause
    exit /b 0
)

echo.
echo Starting trading system...
echo.
echo Press Ctrl+C to stop the bot
echo Logs are saved to: data\logs\
echo.
echo ================================================================================
echo.

REM Start the bot
python main.py

REM Check exit code
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Trading system exited with error
    echo Check the logs in data\logs\ for details
    echo ================================================================================
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Trading system stopped
echo ================================================================================
echo.
pause
