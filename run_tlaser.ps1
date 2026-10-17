# Update this checkout safely, prepare the viewer, and launch the local app.
param(
    [ValidateRange(1, 65535)][int]$Port = 8501,
    [switch]$SkipUpdate,
    [switch]$CheckOnly,
    [switch]$UpdateOnly
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not $SkipUpdate) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Warning 'Git is unavailable; using the local revision.'
    } else {
        $origin = & git remote get-url origin 2>$null
        $branch = & git branch --show-current 2>$null
        $dirty = & git status --porcelain --untracked-files=no
        if ($origin -notmatch '^(https://github\.com/|git@github\.com:)ZhenwenWan/TLaser(?:\.git)?/?$') {
            Write-Warning 'Automatic update requires origin to be the ZhenwenWan/TLaser GitHub repository. Using the local revision.'
        } elseif ($branch -ne 'main' -or $dirty) {
            Write-Warning 'Automatic update skipped: main must be checked out with no changes to tracked files. Local work is preserved.'
        } else {
            Write-Host 'Checking GitHub for TLaser updates...'
            & git fetch origin main
            if ($LASTEXITCODE -ne 0) {
                Write-Warning 'GitHub could not be reached; using the local revision.'
            } else {
                $before = & git rev-parse HEAD
                & git merge --ff-only origin/main
                if ($LASTEXITCODE -ne 0) {
                    throw 'Automatic update stopped. Resolve the branch divergence before launching, or use -SkipUpdate for the local revision. No reset was performed.'
                }
                $after = & git rev-parse HEAD
                if ($after -ne $before) {
                    # Start the newly downloaded launcher rather than continuing old code in memory.
                    $shellPath = (Get-Process -Id $PID).Path
                    $nextArgs = @('-NoProfile', '-File', $PSCommandPath, '-Port', $Port, '-SkipUpdate')
                    if ($CheckOnly) { $nextArgs += '-CheckOnly' }
                    if ($UpdateOnly) { $nextArgs += '-UpdateOnly' }
                    & $shellPath @nextArgs
                    exit $LASTEXITCODE
                }
            }
        }
    }
}
Write-Host "TLaser folder: $PSScriptRoot"
if (Get-Command git -ErrorAction SilentlyContinue) {
    $revision = & git rev-parse --short HEAD 2>$null
    Write-Host "TLaser revision: $revision"
}
if ($UpdateOnly) { exit 0 }

function Start-TLaser([string]$Python, [switch]$Bundled) {
    & $Python -c "import importlib.util,sys; sys.exit(importlib.util.find_spec('plotly') is None)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Installing the 3D viewer dependency (Plotly)...'
        if ($Bundled) {
            & $Python -m pip install --target $installedPackages 'plotly>=6,<7'
        } else {
            & $Python -m pip install 'plotly>=6,<7'
        }
        if ($LASTEXITCODE -ne 0) { throw 'The 3D viewer dependency could not be installed. Check your connection and retry.' }
    }
    & $Python -c "from device_geometry import geometry_3d; from device_model import default_config; f=geometry_3d(default_config()); assert len(f.data) == 30; print('3D viewer ready: Lasers 15-part geometry')"
    if ($LASTEXITCODE -ne 0) { throw '3D geometry validation failed. Check that this checkout includes assets/lasers_geometry.json and its dependencies.' }
    if ($CheckOnly) { exit 0 }
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $Port is already running another app. Stop its PowerShell session with Ctrl+C, then retry. Or run .\run_tlaser.ps1 -Port $($Port + 1)."
    }
    Write-Host "Open http://127.0.0.1:$Port and keep this window running."
    & $Python -m streamlit run app.py --server.port $Port --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
    exit $LASTEXITCODE
}

$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$venvConfig = Join-Path $PSScriptRoot '.venv\pyvenv.cfg'
$storeLauncher = (Test-Path -LiteralPath $venvConfig) -and ((Get-Content -LiteralPath $venvConfig -Raw) -match 'WindowsApps')
if ((Test-Path -LiteralPath $projectPython) -and -not $storeLauncher) {
    & $projectPython -c 'import streamlit' 2>$null
    if ($LASTEXITCODE -eq 0) {
        Start-TLaser $projectPython
    }
}
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$installedPackages = Join-Path $PSScriptRoot '.venv\Lib\site-packages'
if ((Test-Path -LiteralPath $bundledPython) -and (Test-Path -LiteralPath $installedPackages)) {
    $env:PYTHONPATH = $installedPackages
    Start-TLaser $bundledPython -Bundled
}
throw 'Create a working .venv, install requirements.txt, then run python -m streamlit run app.py.'
