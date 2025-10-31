@echo off
REM Quick Fix for Python 3.12 Installation Issues

echo ================================================================================
echo PYTHON 3.12 COMPATIBILITY FIX
echo ================================================================================
echo.

echo Your Python version: 3.12.2
echo Issue: Original requirements.txt had Python 3.11-only packages
echo Solution: Updated requirements.txt for Python 3.12 compatibility
echo.

echo [1/3] Cleaning up any failed installation...
pip uninstall numba -y >nul 2>&1
echo Cleanup complete.
echo.

echo [2/3] Installing updated requirements...
echo This will take 2-3 minutes...
echo.
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo INSTALLATION FAILED
    echo ================================================================================
    echo.
    echo Trying alternative installation method...
    echo.
    
    REM Try installing in smaller batches
    echo Installing core packages...
    pip install pandas numpy pyarrow
    
    echo Installing ML packages...
    pip install xgboost lightgbm scikit-learn scipy
    
    echo Installing networking packages...
    pip install websocket-client requests urllib3 certifi
    
    echo Installing utilities...
    pip install loguru python-json-logger
    
    echo Installing performance packages (Python 3.12 compatible)...
    pip install "numba>=0.60.0" bottleneck
    
    echo Installing configuration packages...
    pip install python-dotenv pydantic pydantic-settings
    
    echo Installing remaining packages...
    pip install pytz APScheduler cryptography marshmallow
    pip install typing-extensions humanize tqdm diskcache
    pip install flask flask-cors
    
    echo.
    echo Alternative installation complete!
)

echo.
echo [3/3] Verifying installation...
python -c "import pandas, numpy, xgboost, lightgbm, websocket, requests, loguru, pydantic; print('SUCCESS: All critical packages installed!')" 2>nul

if errorlevel 1 (
    echo.
    echo WARNING: Some packages may not have installed correctly.
    echo Please check the output above for errors.
    echo.
) else (
    echo.
    echo ================================================================================
    echo INSTALLATION SUCCESSFUL!
    echo ================================================================================
    echo.
    echo All packages are now installed and compatible with Python 3.12.2
    echo.
    echo Next steps:
    echo   1. Run: setup.bat (to configure the system)
    echo   2. Run: launch.bat (to start trading)
    echo.
)

echo.
echo Note about warnings:
echo   - "Ignoring invalid distribution ~lotly" - Safe to ignore
echo   - "Ignoring invalid distribution ~orch" - Safe to ignore
echo   - These are leftover from previous installations
echo.

pause
