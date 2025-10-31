@echo off
REM ML Kraken Pro Live Trader - Configuration Script
echo ============================================
echo ML Kraken Pro Live Trader - Configuration
echo ============================================
echo.
echo This will help you configure the trading system.
echo.

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    call install.bat
)

echo Opening .env file for editing...
echo.
echo Please configure the following:
echo - Add your 5 Kraken API keys (KRAKEN_KEY_1 through KRAKEN_KEY_5)
echo - Set your API secrets (KRAKEN_SECRET_1 through KRAKEN_SECRET_5)
echo - Adjust portfolio size (PORTFOLIO_SIZE_USD)
echo - Select risk mode: conservative, balanced, or aggressive (RISK_MODE)
echo.
echo Press any key to open .env file in notepad...
pause >nul

notepad .env

echo.
echo Configuration saved. You can now run start_bot.bat
pause
