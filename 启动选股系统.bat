@echo off
title AGuxuanGuXiTong

cd /d "D:\work"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python first.
    pause
    exit /b
)

echo Closing old process on port 8510...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8510 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
ping -n 2 127.0.0.1 >nul

echo Starting Stock Screener...
echo.
echo Local:  http://localhost:8510
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do set "ip=%%a"
set "ip=%ip: =%"
echo LAN:    http://%ip%:8510
echo.

python -m streamlit run stock_screener.py --server.port 8510

if errorlevel 1 (
    echo Failed. Try: pip install streamlit akshare baostock
    pause
)
