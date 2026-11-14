$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    $python = $null
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -m venv .venv
    } else {
        $candidate = Get-Command python -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.Source -notmatch 'WindowsApps') { $python = $candidate.Source }
        $codexPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (-not $python -and (Test-Path $codexPython)) { $python = $codexPython }
        if (-not $python) { throw 'Python не найден. Установи Python 3.11+ с python.org, затем перезапусти этот скрипт.' }
        & $python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать виртуальное окружение. Установи Python 3.11+ с python.org.' }
}
& '.venv\Scripts\python.exe' -m pip install -r requirements-local.txt
if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости. Проверь подключение к интернету.' }
if (-not $env:SPORTCENTER_SECRET) {
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $env:SPORTCENTER_SECRET = [Convert]::ToBase64String($bytes)
}
& '.venv\Scripts\python.exe' app.py
