@echo off
REM ML Kraken Pro Live Trader - Start Script
REM This script starts the live trading system

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - STARTING
echo ================================================================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: Configuration file (.env) not found!
    echo.
    echo Creating .env from template...
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo .env file created.
        echo.
        echo IMPORTANT: You must edit .env and add your 5 Kraken API keys!
        echo.
        echo 1. Open: .env
        echo 2. Add your API keys
        echo 3. Run this script again
        echo.
    )
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

REM Check exit code and keep window open
set EXIT_CODE=%ERRORLEVEL%
echo.
echo ================================================================================
if %EXIT_CODE% EQU 0 (
    echo Trading system stopped normally
) else (
    echo ERROR: Trading system exited with error code %EXIT_CODE%
    echo.
    echo Troubleshooting:
    echo   1. Check .env file has all 5 API keys
    echo   2. Run: fix_install.bat to reinstall packages
    echo   3. Check logs in data\logs\ folder
)
echo ================================================================================
echo.
pause
