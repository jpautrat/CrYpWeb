@echo off
REM ML Kraken Pro Live Trader - Safe Start Script
REM This version keeps the window open to show errors

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
        echo.
        echo .env file created successfully.
        echo.
        echo NEXT STEP: You must edit .env and add your 5 Kraken API keys
        echo.
        echo 1. Open .env with Notepad
        echo 2. Find KRAKEN_KEY_1, KRAKEN_SECRET_1, etc.
        echo 3. Replace with your actual API keys from Kraken
        echo 4. Save the file
        echo 5. Run this script again
        echo.
        pause
        exit /b 1
    ) else (
        echo ERROR: .env.example not found!
        pause
        exit /b 1
    )
)

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo.

REM Check if bot folder exists
if not exist "bot" (
    echo ERROR: bot directory not found!
    echo Make sure you're running from the correct folder
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found!
    echo Make sure all files are in the correct location
    pause
    exit /b 1
)

REM Final warning
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                            ⚠️  LIVE TRADING WARNING ⚠️                      ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║  This system will place REAL ORDERS with REAL MONEY                       ║
echo ║                                                                            ║
echo ║  Press Ctrl+C at any time to stop the bot                                 ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

set /p CONFIRM="Type 'START' to begin: "

if not "%CONFIRM%"=="START" (
    echo Start cancelled.
    pause
    exit /b 0
)

echo.
echo ================================================================================
echo Starting trading system...
echo ================================================================================
echo.

REM Run the bot
python main.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo ERROR: Bot exited with error code %ERRORLEVEL%
    echo ================================================================================
    echo.
    echo Common issues:
    echo   1. Missing packages - Run: fix_install.bat
    echo   2. Missing API keys in .env file
    echo   3. Invalid configuration in .env
    echo.
    echo Check the error message above for details.
    echo.
)

pause
