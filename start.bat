@echo off
title LUXE.TECH Fullstack Launcher
echo ========================================================
echo  Starting LUXE.TECH Fashion Intelligence Platform
echo ========================================================
start "LUXE.TECH Backend" cmd /k "%~dp0run_backend.bat"
timeout /t 3 /nobreak >nul
start "LUXE.TECH Frontend" cmd /k "%~dp0run_frontend.bat"
echo.
echo Platform is launching!
echo Backend:  http://127.0.0.1:8000 (Docs: http://127.0.0.1:8000/docs)
echo Frontend: http://127.0.0.1:5173
echo ========================================================
