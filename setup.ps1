$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    $arenaPython = $null
    foreach ($arenaCandidate in @('py', 'python', 'python3')) {
        if (-not (Get-Command $arenaCandidate -ErrorAction SilentlyContinue)) { continue }
        $arenaArgs = if ($arenaCandidate -eq 'py') { @('-3.11') } else { @() }
        try {
            $arenaFound = & $arenaCandidate @arenaArgs -c 'import sys; sys.exit(1) if sys.version_info[:2] != (3,11) or sys.maxsize <= 2**32 else None; print(sys.executable)' 2>$null
        } catch { continue }
        if ($LASTEXITCODE -eq 0 -and $arenaFound) {
            $arenaPython = ($arenaFound | Select-Object -Last 1).Trim()
            break
        }
    }
    if (-not $arenaPython) { throw 'Install Python 3.11 (64-bit) from python.org, then run Setup CHRONO ARENA.cmd again.' }
    & $arenaPython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 (64-bit) and try again.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' scripts\download_models.py
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
& '.\.venv\Scripts\python.exe' -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Host 'Ready. Open Launch CHRONO ARENA.cmd for webcam play, or Launch Demo.cmd without a camera.'
