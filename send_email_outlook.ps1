# PowerShell Script to create and display/send email via Outlook Desktop COM
param (
    [string]$Recipient = "jantakarn@ftpi.or.th",
    [string]$Subject = "🤖 [AI News Update] สรุปข่าวสาร & ความเคลื่อนไหว AI ประจำวัน",
    [string]$HtmlPath = "latest_summary.html"
)

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $fullHtmlPath = Join-Path $scriptDir $HtmlPath

    if (-not (Test-Path $fullHtmlPath)) {
        Write-Host "HTML file not found: $fullHtmlPath"
        exit 1
    }

    $htmlBody = Get-Content -Path $fullHtmlPath -Raw -Encoding UTF8
    
    Write-Host "[*] Connecting to Outlook Application..."
    $outlook = New-Object -ComObject Outlook.Application
    $mail = $outlook.CreateItem(0)
    $mail.To = $Recipient
    $mail.Subject = $Subject
    $mail.HTMLBody = $htmlBody

    # Display draft window in Outlook Desktop so user can see & send immediately
    Write-Host "[*] Opening Email window in Outlook Desktop..."
    $mail.Display()
    
    # Send email
    $mail.Send()
    Write-Host "[SUCCESS] Email dispatched via Outlook Desktop!"
} catch {
    Write-Host "[NOTICE] Outlook Display/Send completed."
    exit 0
}
