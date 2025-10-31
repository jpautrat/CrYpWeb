@echo off
REM ML Kraken Pro Live Trader - Quick Start (All-in-One)
REM This script does everything: install, configure, and start

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - QUICK START
echo ================================================================================
echo.

REM Step 1: Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo OK
echo.

REM Step 2: Install packages if needed
echo [2/4] Checking packages...
python -c "import pandas, numpy, xgboost" >nul 2>&1
if errorlevel 1 (
    echo Installing packages... (this takes 2-3 minutes)
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ERROR: Package installation failed
        pause
        exit /b 1
    )
    echo Packages installed OK
) else (
    echo Packages already installed OK
)
echo.

REM Step 3: Create .env if missing
echo [3/4] Checking configuration...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Created .env file from template
        echo.
        echo ============================================================
        echo IMPORTANT: You must add your Kraken API keys to .env
        echo ============================================================
        echo.
        echo Opening .env in Notepad...
        echo.
        echo Find these lines and replace with your actual keys:
        echo   KRAKEN_KEY_1=YOUR_API_KEY_HERE
        echo   KRAKEN_SECRET_1=YOUR_API_SECRET_HERE
        echo   (repeat for all 5 key pairs)
        echo.
        echo After adding your keys:
        echo   1. Save the file
        echo   2. Close Notepad
        echo   3. Run this script again
        echo.
        notepad .env
        pause
        exit /b 0
    ) else (
        echo ERROR: .env.example not found
        pause
        exit /b 1
    )
) else (
    echo Configuration file exists OK
)
echo.

REM Step 4: Start the bot
echo [4/4] Starting trading system...
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                       ⚠️  LIVE TRADING WARNING ⚠️                           ║
echo ║                                                                            ║
echo ║  This system uses REAL MONEY and places REAL ORDERS                       ║
echo ║  Press Ctrl+C at any time to stop                                         ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

set /p START="Type 'GO' to start trading: "
if not "%START%"=="GO" (
    echo Cancelled
    pause
    exit /b 0
)

echo.
echo Starting...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR OCCURRED
    echo ================================================================================
    echo.
    echo Common fixes:
    echo   1. Make sure .env has all 5 API key pairs filled in
    echo   2. Run: fix_install.bat
    echo   3. Check data\logs\ for error details
    echo.
)

pause
