# Build the Windows exe and installer locally: .\scripts\build_exe.ps1
# Needs Python 3.11+ and (for the installer) Inno Setup 6 (choco install innosetup).
$ErrorActionPreference = "Stop"
python -m pip install -e ".[build]"
Push-Location packaging
python -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build storelistingkit.spec
$env:SLK_ONEFILE = "1"
python -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build\onefile storelistingkit.spec
Remove-Item Env:\SLK_ONEFILE
Pop-Location
.\dist\StoreListingKit.exe selftest
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) { & $iscc packaging\installer.iss } else { Write-Warning "Inno Setup not found; skipped installer." }
Get-ChildItem dist
