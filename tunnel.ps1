$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
$localCloudflared = Join-Path $PSScriptRoot 'tools\cloudflared.exe'
if ($cloudflared) { $cloudflaredPath = $cloudflared.Source }
elseif (Test-Path $localCloudflared) { $cloudflaredPath = $localCloudflared }
else { throw 'cloudflared не найден. Установи его командой: winget install --id Cloudflare.cloudflared' }
Write-Host 'Проверь, что сайт уже запущен командой .\run.ps1. Ссылка появится ниже.'
& $cloudflaredPath tunnel --url http://127.0.0.1:5000
