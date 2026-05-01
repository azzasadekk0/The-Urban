# Start The Urban (PowerShell)
# Usage: .\start.ps1

$PYTHON  = "C:\Users\sonma\AppData\Local\Programs\Python\Python312\python.exe"
$ROOT    = Split-Path -Parent $MyInvocation.MyCommand.Path
$BPORT   = 8001
$FPORT   = 3000

Write-Host "=== The Urban - AI Expert System ===" -ForegroundColor Cyan
Write-Host "Using Python: $PYTHON" -ForegroundColor DarkGray

# -- Load .env variables into process environment ----------------------------
$envFile = Join-Path $ROOT ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

# -- Disable LangSmith tracing -----------------------------------------------
$env:LANGCHAIN_TRACING_V2 = "false"
$env:LANGCHAIN_TRACING     = "false"
$env:LANGSMITH_API_KEY     = ""
$env:LANGCHAIN_API_KEY     = ""
$env:ANONYMIZED_TELEMETRY  = "false"
$env:PYTHONIOENCODING      = "utf-8"

# -- Kill any stale process on our ports + ngrok ----------------------------
foreach ($port in @($BPORT, $FPORT)) {
    $pids = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique
    foreach ($p in $pids) {
        if ($p -gt 0) {
            Write-Host "Killing stale PID $p on port $port" -ForegroundColor DarkYellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}
# Kill any leftover ngrok.exe (prevents ERR_NGROK_334 on restart)
Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

Write-Host ""
Write-Host "Starting FastAPI backend  -> http://localhost:${BPORT}/docs" -ForegroundColor Green
Write-Host "Starting Next.js UI       -> http://localhost:${FPORT}" -ForegroundColor Green
Write-Host ""

# -- Backend -----------------------------------------------------------------
$backendCmd = @"
  `$env:LANGCHAIN_TRACING_V2 = 'false'
  `$env:LANGCHAIN_TRACING     = 'false'
  `$env:LANGSMITH_API_KEY     = ''
  `$env:LANGCHAIN_API_KEY     = ''
  `$env:ANONYMIZED_TELEMETRY  = 'false'
  `$env:PYTHONIOENCODING      = 'utf-8'
  cd '$ROOT'
  & '$PYTHON' -m uvicorn backend.main:app --host 0.0.0.0 --port $BPORT --reload
"@
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 4

# -- Frontend (Next.js) -------------------------------------------------------
$frontendCmd = "cd '$ROOT\Frontend'; pnpm run dev"
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 3

# -- Ngrok tunnel (public live link) -----------------------------------------
$ngrokToken = [System.Environment]::GetEnvironmentVariable("NGROK_AUTH_TOKEN", "Process")
if ($ngrokToken -and $ngrokToken -ne "") {
    Write-Host ""
    Write-Host "Starting ngrok tunnel..." -ForegroundColor Magenta
    $ngrokCmd = "cd '$ROOT'; & '$PYTHON' ngrok_tunnel.py $FPORT '$ngrokToken'"
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-ExecutionPolicy", "Bypass", "-Command", $ngrokCmd
    
    # Wait for tunnel to establish
    Start-Sleep -Seconds 7
    try {
        $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $publicUrl = $tunnels.tunnels[0].public_url
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "  LIVE PUBLIC URL: $publicUrl" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host ""
    } catch {
        Write-Host "  [NGROK] Tunnel started but could not fetch URL directly." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [NGROK] No NGROK_AUTH_TOKEN in .env - skipping tunnel." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Both services started!" -ForegroundColor Yellow
Write-Host "  Backend API docs -> http://localhost:${BPORT}/docs"
Write-Host "  Next.js UI       -> http://localhost:${FPORT}"
Write-Host ""
