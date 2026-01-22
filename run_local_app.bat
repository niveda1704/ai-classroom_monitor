@echo off
echo ========================================
echo    AI Classroom Monitor - Local App
echo ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install/update requirements if needed
if not exist "venv\installed.flag" (
    echo Installing dependencies...
    pip install -r local_app\requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo. > venv\installed.flag
)

:: Run the application
echo.
echo Starting AI Classroom Monitor...
echo.
python -m local_app.main

:: Deactivate on exit
call venv\Scripts\deactivate.bat
