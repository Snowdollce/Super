@echo off
:: Batch script to register Windows Task Scheduler job
set TASK_NAME=Daily_AI_News_Email_FTPI
set SCRIPT_PATH=%~dp0ai_news_fetcher.py

echo Registering Windows Task Scheduler Job...
schtasks /create /tn "%TASK_NAME%" /tr "python.exe \"%SCRIPT_PATH%\"" /sc daily /st 09:00 /f

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Task "%TASK_NAME%" has been scheduled daily at 09:00 AM.
) else (
    echo ERROR: Failed to create scheduled task.
)
