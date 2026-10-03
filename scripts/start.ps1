$ErrorActionPreference = 'Stop'
$galleryRoot = Split-Path -Parent $PSScriptRoot
$galleryPython = Join-Path $galleryRoot 'backend\.venv\Scripts\python.exe'
$galleryNode = (Get-Command node -ErrorAction Stop).Source
$galleryVite = Join-Path $galleryRoot 'frontend\node_modules\vite\bin\vite.js'
if (!(Test-Path -LiteralPath $galleryPython) -or !(Test-Path -LiteralPath $galleryVite)) {
    throw 'Install backend and frontend dependencies first; see README.md.'
}
foreach ($galleryPort in @(8040, 5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $galleryPort -ErrorAction SilentlyContinue) {
        throw "Port $galleryPort is occupied. No process has been stopped."
    }
}
$galleryLogs = Join-Path $galleryRoot '.local'
New-Item -ItemType Directory -Force -Path $galleryLogs | Out-Null
$galleryBackend = Start-Process -FilePath $galleryPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8040','--workers','1','--limit-concurrency','16') -WorkingDirectory (Join-Path $galleryRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $galleryLogs 'backend.out.log') -RedirectStandardError (Join-Path $galleryLogs 'backend.err.log') -PassThru
try {
    $galleryFrontend = Start-Process -FilePath $galleryNode -ArgumentList @(('"' + $galleryVite + '"'),'--host','127.0.0.1','--port','5173') -WorkingDirectory (Join-Path $galleryRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $galleryLogs 'frontend.out.log') -RedirectStandardError (Join-Path $galleryLogs 'frontend.err.log') -PassThru
} catch {
    Stop-Process -Id $galleryBackend.Id -ErrorAction SilentlyContinue
    throw
}
@{ backend = $galleryBackend.Id; frontend = $galleryFrontend.Id } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $galleryLogs 'processes.json')
$galleryDeadline = [DateTime]::UtcNow.AddSeconds(15)
$galleryReady = $false
while ([DateTime]::UtcNow -lt $galleryDeadline) {
    try {
        $galleryHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8040/api/health' -TimeoutSec 1
        $galleryWeb = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -TimeoutSec 1
        $galleryApiPort = Get-NetTCPConnection -State Listen -LocalPort 8040 | Select-Object -First 1
        $galleryWebPort = Get-NetTCPConnection -State Listen -LocalPort 5173 | Select-Object -First 1
        $galleryApi = Get-CimInstance Win32_Process -Filter "ProcessId = $($galleryApiPort.OwningProcess)"
        if ($galleryHealth.status -eq 'ok' -and $galleryWeb.StatusCode -eq 200 -and $galleryWebPort.OwningProcess -eq $galleryFrontend.Id -and ($galleryApi.ProcessId -eq $galleryBackend.Id -or $galleryApi.ParentProcessId -eq $galleryBackend.Id)) {
            @{ backend = $galleryApi.ProcessId; backendLauncher = $galleryBackend.Id; frontend = $galleryFrontend.Id } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $galleryLogs 'processes.json')
            $galleryReady = $true
            break
        }
    } catch { }
    Start-Sleep -Milliseconds 150
}
if (!$galleryReady) {
    & (Join-Path $PSScriptRoot 'stop.ps1')
    throw 'Gallery did not become ready. Check .local/*.log; preview processes were stopped.'
}
Write-Output 'Local gallery: http://127.0.0.1:5173/'
