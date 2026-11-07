$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExecutable = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Install backend dependencies first. See README.md.'
}
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
foreach ($port in @(8010, 5175)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop that service or use the manual README commands."
    }
}
$runtimeDirectory = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null
$processes = @()
try {
    $backend = Start-Process -FilePath $pythonExecutable -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8010') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDirectory 'backend.log') -RedirectStandardError (Join-Path $runtimeDirectory 'backend-error.log')
    $processes += @{ id = $backend.Id; started = $backend.StartTime.ToUniversalTime().Ticks }
    $frontend = Start-Process -FilePath $nodeExecutable -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5175','--strictPort') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDirectory 'frontend.log') -RedirectStandardError (Join-Path $runtimeDirectory 'frontend-error.log')
    $processes += @{ id = $frontend.Id; started = $frontend.StartTime.ToUniversalTime().Ticks }
    ConvertTo-Json -InputObject $processes | Set-Content -LiteralPath (Join-Path $runtimeDirectory 'processes.json')
    Write-Host 'Starting SubstiGraph AI at http://127.0.0.1:5175'
    Write-Host 'API: http://127.0.0.1:8010/docs. Startup may take a few seconds.'
    Write-Host 'Logs: .runtime/. Stop these processes with .\stop.ps1.'
} catch {
    foreach ($entry in $processes) { Stop-Process -Id $entry.id -ErrorAction SilentlyContinue }
    throw
}
