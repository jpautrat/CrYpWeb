@echo off
REM ML Kraken Pro Live Trader - Launch Script
REM Starts the trading system with configuration validation

setlocal enabledelayedexpansion

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - LAUNCHER
echo ================================================================================
echo.

REM Check if configured
if not exist ".env" (
    echo ERROR: System not configured!
    echo.
    echo Please run setup.bat first to configure the system.
    echo.
    pause
    exit /b 1
)

REM Pre-flight checks
echo [Pre-Flight Checks]
echo.

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found
    pause
    exit /b 1
)
echo   Python: OK

REM Check dependencies
echo Checking dependencies...
python -c "import pandas, numpy, xgboost, lightgbm, websocket, requests" >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Dependencies not installed
    echo   Please run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo   Dependencies: OK

REM Check configuration
echo Validating configuration...
python -c "from bot.config import get_settings; get_settings()" >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Invalid configuration
    echo   Please run setup.bat or edit .env manually
    pause
    exit /b 1
)
echo   Configuration: OK

REM Check data directories
if not exist "data" (
    echo   Creating data directories...
    mkdir data\raw data\features data\models data\logs data\logs\audit
)
echo   Data directories: OK

REM Check kill switch
if exist "data\.kill_switch" (
    echo.
    echo WARNING: Kill switch file detected!
    echo   Location: data\.kill_switch
    echo.
    set /p REMOVE_KS="Remove kill switch and continue? (Y/N): "
    if /i "!REMOVE_KS!"=="Y" (
        del "data\.kill_switch"
        echo   Kill switch removed
    ) else (
        echo   Launch cancelled
        pause
        exit /b 0
    )
)

echo.
echo All checks passed!
echo.

REM Load and display configuration
echo [Configuration Summary]
echo.
for /f "tokens=1,2 delims==" %%a in (.env) do (
    set line=%%a
    if "!line:~0,1!" NEQ "#" (
        if "!line:~0,1!" NEQ "" (
            if "%%a"=="PORTFOLIO_SIZE_USD" echo Portfolio Size: $%%b
            if "%%a"=="RISK_MODE" echo Risk Mode: %%b
            if "%%a"=="UNIVERSE_SIZE" echo Trading Pairs: %%b
            if "%%a"=="CONFIDENCE_THRESHOLD" echo Confidence Threshold: %%b
            if "%%a"=="MAX_DAILY_DRAWDOWN_PCT" echo Max Daily Drawdown: %%b%%
        )
    )
)
echo.

REM Final warning
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                            ⚠️  CRITICAL WARNING ⚠️                          ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║  This is a LIVE TRADING system that will:                                 ║
echo ║  • Place REAL ORDERS on Kraken exchange                                   ║
echo ║  • Use REAL MONEY from your account                                       ║
echo ║  • Execute trades automatically based on ML models                        ║
echo ║                                                                            ║
echo ║  EMERGENCY CONTROLS:                                                      ║
echo ║  • Press Ctrl+C to stop gracefully                                        ║
echo ║  • Create file "data\.kill_switch" to emergency halt                      ║
echo ║  • Use kill switch password from .env                                     ║
echo ║                                                                            ║
echo ║  MONITORING:                                                              ║
echo ║  • Watch this window for live activity                                    ║
echo ║  • Check logs in: data\logs\                                              ║
echo ║  • System collects data for 24h before full ML training                   ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Confirmation
set /p CONFIRM="Type 'START' (in capitals) to launch the trading bot: "

if not "%CONFIRM%"=="START" (
    echo.
    echo Launch cancelled by user.
    echo.
    pause
    exit /b 0
)

echo.
echo ================================================================================
echo LAUNCHING TRADING SYSTEM
echo ================================================================================
echo.
echo Starting at: %date% %time%
echo.
echo Press Ctrl+C to stop the bot
echo Logs: data\logs\trader_%date:~-4%%date:~-7,2%%date:~-10,2%.log
echo.
echo ================================================================================
echo.

REM Launch the bot
python main.py

REM Check exit code
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ================================================================================
if %EXIT_CODE% EQU 0 (
    echo Trading system stopped normally
) else (
    echo Trading system exited with error code: %EXIT_CODE%
    echo Check logs in data\logs\ for details
)
echo ================================================================================
echo.
echo Stopped at: %date% %time%
echo.
pause
