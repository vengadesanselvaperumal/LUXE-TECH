@echo off
title LUXE.TECH Backend Server
echo ========================================================
echo  LUXE.TECH — FastApi Intelligence Platform Backend
echo ========================================================
cd /d "%~dp0backend"
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
)
pause
