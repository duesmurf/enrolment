@echo off
REM ============================================================
REM Student Enrolment Agent - Quick Setup Script (Windows CMD)
REM Run this in Command Prompt: setup.bat
REM ============================================================

echo.
echo ============================================
echo   Student Enrolment Agent - Quick Setup
echo ============================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python not found!
    echo   Install Python from: https://www.python.org/downloads/
    exit /b 1
)
python --version

REM Create virtual environment
echo.
echo [2/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo   Created: .\venv
) else (
    echo   Already exists: .\venv
)

REM Activate and install
echo.
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo   Done!

REM Create directories
echo.
echo [4/4] Setting up project structure...
if not exist "credentials" mkdir credentials
if not exist "output" mkdir output
if not exist ".env" copy .env.example .env >nul 2>&1
echo   Created: credentials\ output\ .env

REM Check for credentials
echo.
echo ============================================
if exist "credentials\credentials.json" (
    echo   READY! Credentials found.
    echo.
    echo   Run:  python main.py --demo    (test)
    echo   Run:  python main.py           (full pipeline)
) else (
    echo   ALMOST READY!
    echo.
    echo   Next step: Place your credentials.json file:
    echo     copy %USERPROFILE%\Downloads\credentials.json credentials\
    echo.
    echo   Then run:  python main.py --setup  (verify)
    echo   Then run:  python main.py --demo   (test)
)
echo ============================================
echo.
pause
