# PowerShell Script to register the Daily AI News Automation task robustly
$taskName = "Daily_AI_News_Email_FTPI"
$pythonPath = "C:\Users\Jantakarn\AppData\Local\Programs\Python\Python314\python.exe"
$workingDir = "c:\Users\Jantakarn\OneDrive - The foundation for Thailand Productivity Institute (Branch 1)\0_WebApp_Building\Email_Auto\AI Reseach"
$scriptPath = Join-Path $workingDir "ai_news_fetcher.py"

Write-Host "============================================================"
Write-Host " Registering Windows Scheduled Task for Daily AI News Email"
Write-Host "============================================================"
Write-Host "[*] Python Path : $pythonPath"
Write-Host "[*] Working Dir : $workingDir"
Write-Host "[*] Script Path : $scriptPath"

# 1. Check if python.exe exists
if (-not (Test-Path $pythonPath)) {
    Write-Error "Python executable not found at $pythonPath. Please update the path in this script."
    exit 1
}

# 2. Unregister existing task if it exists
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "[*] Unregistering existing task: $taskName..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# 3. Create Task Action
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir

# 4. Create Trigger (Daily at 09:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At "9:00AM"

# 5. Create Settings
# Allow running on battery, wake computer, and run as soon as possible if missed
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun

# 6. Register Task
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Daily automated AI News aggregator and email delivery for FTPI" | Out-Null
    Write-Host ""
    Write-Host "SUCCESS: Scheduled Task '$taskName' has been registered successfully!"
    Write-Host "Trigger Time: 09:00 AM daily"
    Write-Host "Battery settings: Enabled (will run on battery power)"
    Write-Host "Run missed settings: Enabled (will run if machine was asleep/offline at 9:00 AM)"
} catch {
    Write-Error "Failed to register scheduled task: $_"
    exit 1
}
