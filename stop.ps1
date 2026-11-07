$ErrorActionPreference = 'Stop'
$stateFile = Join-Path $PSScriptRoot '.runtime\processes.json'
if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host 'No saved SubstiGraph processes.'
    return
}
foreach ($entry in (Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json)) {
    $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
    # Check creation time so a recycled Windows process ID is never stopped.
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $entry.started) {
        Stop-Process -Id $process.Id
    }
}
Remove-Item -LiteralPath $stateFile
Write-Host 'Stopped SubstiGraph processes started by start.ps1.'
