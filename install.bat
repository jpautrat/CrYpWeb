@echo off
REM ML Kraken Pro Live Trader - Installation Script
echo ============================================
echo ML Kraken Pro Live Trader - Installation
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

echo [2/5] Upgrading pip...
python -m pip install --upgrade pip

echo [3/5] Installing dependencies...
python -m pip install pandas numpy pyarrow xgboost lightgbm scikit-learn loguru websocket-client requests scipy numba

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [4/5] Creating data directories...
if not exist "data\raw" mkdir "data\raw"
if not exist "data\features" mkdir "data\features"
if not exist "data\models" mkdir "data\models"
if not exist "data\logs" mkdir "data\logs"
if not exist "data\logs\audit" mkdir "data\logs\audit"

echo [5/5] Setup complete!
echo.
echo IMPORTANT: Configure your API keys in .env file before running
echo.
pause
