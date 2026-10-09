# Local launcher; recovers this checkout's dependencies if its old venv launcher is broken.
param([int]$Port = 8501)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$venvConfig = Join-Path $PSScriptRoot '.venv\pyvenv.cfg'
$storeLauncher = (Test-Path -LiteralPath $venvConfig) -and ((Get-Content -LiteralPath $venvConfig -Raw) -match 'WindowsApps')
if ((Test-Path -LiteralPath $projectPython) -and -not $storeLauncher) {
    & $projectPython -c 'import streamlit' 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $projectPython -m streamlit run app.py --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
        exit $LASTEXITCODE
    }
}
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$installedPackages = Join-Path $PSScriptRoot '.venv\Lib\site-packages'
if ((Test-Path -LiteralPath $bundledPython) -and (Test-Path -LiteralPath $installedPackages)) {
    $env:PYTHONPATH = $installedPackages
    & $bundledPython -m streamlit run app.py --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
    exit $LASTEXITCODE
}
throw 'Create a working .venv, install requirements.txt, then run python -m streamlit run app.py.'
