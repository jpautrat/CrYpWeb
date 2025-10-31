@echo off
REM ML Kraken Pro Live Trader - Configuration Helper
REM This script validates configuration from .env file

echo ================================================================================
echo ML KRAKEN PRO LIVE TRADER - CONFIGURATION VALIDATOR
echo ================================================================================
echo.

REM Check if .env exists, if not create from example
if not exist ".env" (
    echo .env file not found. Creating from template...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo .env file created from .env.example
        echo.
        echo IMPORTANT: Edit .env file and add your 5 Kraken API keys
        echo           before running the bot!
        echo.
    ) else (
        echo ERROR: .env.example not found
        echo Please ensure .env.example exists in this directory
        pause
        exit /b 1
    )
)

:menu
echo.
echo CONFIGURATION MENU:
echo -------------------
echo 1. View current configuration
echo 2. Test API connectivity
echo 3. Set risk mode (Conservative/Balanced/Aggressive)
echo 4. Set portfolio size
echo 5. Edit configuration file manually
echo 6. Validate configuration
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto view_config
if "%choice%"=="2" goto test_api
if "%choice%"=="3" goto set_risk_mode
if "%choice%"=="4" goto set_portfolio
if "%choice%"=="5" goto edit_config
if "%choice%"=="6" goto validate_config
if "%choice%"=="7" goto end

echo Invalid choice. Please try again.
goto menu

:view_config
echo.
echo Current Configuration:
echo ---------------------
type .env | findstr /V "KEY SECRET PASSWORD"
echo.
echo (API keys and passwords hidden for security)
pause
goto menu

:test_api
echo.
echo Testing API connectivity...
echo This requires valid API keys in .env
echo.
python -c "from bot.config import get_settings; from bot.core import AuthManager, KrakenRestClient; settings = get_settings(); key = settings.api_keys[0]; auth = AuthManager(key['key'], key['secret']); client = KrakenRestClient(auth); result = client.get_server_time(); print('✓ API connection successful!'); print(f'Server time: {result}')"
if errorlevel 1 (
    echo.
    echo ✗ API connection failed
    echo Please check your API keys in .env
)
pause
goto menu

:set_risk_mode
echo.
echo Risk Modes:
echo -----------
echo 1. Conservative (1%% per trade, 5%% daily limit)
echo 2. Balanced (3%% per trade, 15%% daily limit) [DEFAULT]
echo 3. Aggressive (5%% per trade, 25%% daily limit)
echo.
set /p risk_choice="Select risk mode (1-3): "

if "%risk_choice%"=="1" (
    powershell -Command "(Get-Content .env) -replace 'RISK_MODE=.*', 'RISK_MODE=conservative' | Set-Content .env"
    echo Risk mode set to: Conservative
)
if "%risk_choice%"=="2" (
    powershell -Command "(Get-Content .env) -replace 'RISK_MODE=.*', 'RISK_MODE=balanced' | Set-Content .env"
    echo Risk mode set to: Balanced
)
if "%risk_choice%"=="3" (
    powershell -Command "(Get-Content .env) -replace 'RISK_MODE=.*', 'RISK_MODE=aggressive' | Set-Content .env"
    echo Risk mode set to: Aggressive
)
pause
goto menu

:set_portfolio
echo.
set /p portfolio="Enter portfolio size in USD (200-10000): "
powershell -Command "(Get-Content .env) -replace 'PORTFOLIO_SIZE_USD=.*', 'PORTFOLIO_SIZE_USD=%portfolio%' | Set-Content .env"
echo Portfolio size set to: $%portfolio%
pause
goto menu

:edit_config
echo.
echo Opening .env in default text editor...
start notepad .env
pause
goto menu

:validate_config
echo.
echo Validating configuration...
python -c "from bot.config import get_settings; settings = get_settings(); print('✓ Configuration is valid'); print(f'Portfolio: ${settings.portfolio_size_usd}'); print(f'Risk Mode: {settings.risk_mode.value}'); print(f'Universe Size: {settings.universe_size} pairs'); print(f'API Keys: {len(settings.api_keys)} configured')"
if errorlevel 1 (
    echo.
    echo ✗ Configuration validation failed
    echo Please check your .env file for errors
)
pause
goto menu

:end
echo.
echo Configuration complete.
echo.
