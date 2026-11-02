<#
Builds dist\Accentually\ (PyInstaller) and dist\Accentually-Setup.exe (Inno Setup).
Usage: .\build.ps1            # version taken from core\version.py
Requires: pip install -r requirements-build.txt, and Inno Setup 6 (iscc.exe).
#>
$ErrorActionPreference = 'Continue'  # PyInstaller logs to stderr; failures are caught via $LASTEXITCODE
Set-Location $PSScriptRoot

$version = (python -c "from core.version import __version__; print(__version__)").Trim()
Write-Host "Building Accentually $version"

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm --clean --windowed --name Accentually `
    --icon assets\app_icon.ico --add-data "assets;assets" `
    --collect-submodules comtypes --hidden-import comtypes.automation `
    quick_accent.py
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "Inno Setup 6 not found. Install it (winget install JRSoftware.InnoSetup)." }

& $iscc "/DAppVersion=$version" installer\accentually.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }

$setup = "dist\Accentually-Setup.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  Accentually-Setup.exe" | Set-Content -Encoding ascii "$setup.sha256"
Write-Host "Done: $setup  (sha256 $hash)"
