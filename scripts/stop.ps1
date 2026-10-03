$ErrorActionPreference = 'Stop'
$galleryRoot = Split-Path -Parent $PSScriptRoot
$galleryPidFile = Join-Path $galleryRoot '.local\processes.json'
if (!(Test-Path -LiteralPath $galleryPidFile)) { return }
$galleryPids = Get-Content -LiteralPath $galleryPidFile -Raw | ConvertFrom-Json
$galleryLauncherId = if ($galleryPids.backendLauncher) { $galleryPids.backendLauncher } else { $galleryPids.backend }
$galleryLauncher = Get-CimInstance Win32_Process -Filter "ProcessId = $galleryLauncherId" -ErrorAction SilentlyContinue
if ($galleryLauncher -and $galleryLauncher.ExecutablePath -and $galleryLauncher.ExecutablePath.StartsWith((Join-Path $galleryRoot 'backend\.venv')) -and $galleryLauncher.CommandLine.Contains('uvicorn app.main:app')) {
    # Windows venv python may launch the actual API as a child process.
    $galleryPorts = Get-NetTCPConnection -State Listen -LocalPort 8040 -ErrorAction SilentlyContinue
    foreach ($galleryPort in $galleryPorts) {
        $galleryChild = Get-CimInstance Win32_Process -Filter "ProcessId = $($galleryPort.OwningProcess)" -ErrorAction SilentlyContinue
        if ($galleryChild -and $galleryChild.ParentProcessId -eq $galleryLauncherId -and $galleryChild.CommandLine.Contains('uvicorn app.main:app')) {
            Stop-Process -Id $galleryChild.ProcessId -ErrorAction SilentlyContinue
        }
    }
}
foreach ($galleryPid in @($galleryLauncherId, $galleryPids.frontend)) {
    $galleryProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $galleryPid" -ErrorAction SilentlyContinue
    if ($galleryProcess -and $galleryProcess.CommandLine -and ($galleryProcess.CommandLine.Contains($galleryRoot) -or ($galleryProcess.ExecutablePath -and $galleryProcess.ExecutablePath.StartsWith((Join-Path $galleryRoot 'backend\.venv'))))) {
        Stop-Process -Id $galleryPid -ErrorAction SilentlyContinue
    }
}
Remove-Item -LiteralPath $galleryPidFile
Write-Output 'Recorded gallery preview processes stopped.'
