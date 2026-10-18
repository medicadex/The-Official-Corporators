@echo off
title Wealthbridge Cooperative Platform Server (WMC)
color 0A

echo ===============================================================================
echo   WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
echo   One-Click Web Application & Backend Server Launcher
echo   Official Contact: wealthbridge.coopsociety@gmail.com
echo ===============================================================================
echo.

:: Ensure working directory is this folder
cd /d "%~dp0"

:: 1. Check Python installation
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.10+ and make sure to check "Add Python to PATH".
    pause
    exit /b
)
echo [+] Python detected successfully.

:: 2. Launch FastAPI / Uvicorn Server in new process
echo [*] Starting FastAPI Backend Service on port 8088...
start "Wealthbridge Backend Service [Port 8088]" cmd /k "python -m uvicorn wbmf_api:app --host 127.0.0.1 --port 8088 --reload"

:: 3. Wait briefly for backend initialization
timeout /t 3 /nobreak >nul

:: 4. Launch Web App & Swagger Docs in Default Web Browser
echo [*] Opening Web Application in your default browser...
start "" "http://127.0.0.1:8088/"

echo.
echo ===============================================================================
echo   [+] WEALTHBRIDGE COOPERATIVE SYSTEM IS LIVE!
echo ===============================================================================
echo   - Web Platform:  http://127.0.0.1:8088/
echo   - Backend API:   http://127.0.0.1:8088
echo   - Swagger Docs:  http://127.0.0.1:8088/docs
echo   - Database:      MySQL 8.0 (Schema: wbmf on port 3306)
echo ===============================================================================
echo.
echo Leave this window or the backend window open while using the platform.
echo To stop the server, simply close the backend window.
echo.
pause
