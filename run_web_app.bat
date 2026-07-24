@echo off
title AI News & Copywriter Assistant
echo ============================================================
echo  Starting AI News & Facebook Copywriter Local Server
echo ============================================================
echo [*] Launching web browser at http://localhost:5000...
start "" "http://localhost:5000"
echo [*] Starting Python backend server...
python app.py
pause
