@echo off
title LUXE.TECH Frontend Server
echo ========================================================
echo  LUXE.TECH — Frontend Development Server
echo ========================================================
cd /d "%~dp0frontend"
call npx vite --host 127.0.0.1 --port 5173
pause
