param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]] $WranglerArgs
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$nodeDir = Join-Path $PSScriptRoot 'tools\node-portable\node-v24.11.0-win-x64'
if (-not (Test-Path (Join-Path $nodeDir 'npx.cmd'))) {
    throw 'Bundled Node.js/npm is missing. Run: uv run python tools/bootstrap_node.py'
}
$env:PATH = "$nodeDir;$env:PATH"
& uv run pywrangler @WranglerArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
