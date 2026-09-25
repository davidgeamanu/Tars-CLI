# Builds dist\tars-windows-x64.zip: python.org's embeddable Python with TARS and its libraries
# inside, plus what install.ps1 needs to set it up. Run from anywhere:
#
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
#
# Then install the result with:
#   powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -ZipFile dist\tars-windows-x64.zip
#
# GitHub Actions runs this same script for every release.
param(
    [string]$Python = "python"      # any Python 3.10+; it only runs pip during the build
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location (Split-Path $PSScriptRoot -Parent)

# The Python bundled into the app
$bundledPython = "3.14.7"
$pyMinor = ($bundledPython -split "\.")[0..1] -join "."        # 3.14
$abi = "cp" + ($pyMinor -replace "\.", "")                     # cp314

# Run a program and stop the build if it fails (PowerShell doesn't do that for .exe files)
function Run {
    $exe, $rest = $args
    & $exe @rest
    if ($LASTEXITCODE -ne 0) { throw "'$exe $rest' failed with exit code $LASTEXITCODE" }
}

$version = [regex]::Match((Get-Content -Raw tars\__init__.py), '__version__ = "(.+?)"').Groups[1].Value
Write-Host "Building TARS $version with Python $bundledPython"

# 1. A build environment, only used to run pip
$venv = "build\venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Run $Python -m venv $venv
}
$py = "$venv\Scripts\python.exe"
Run $py -m pip install --quiet --upgrade pip

# 2. python.org's embeddable Python. Its python.exe is signed by the Python Software
#    Foundation, which is what lets it run under Windows Smart App Control.
$embedZip = "build\cache\python-$bundledPython-embed-amd64.zip"
if (-not (Test-Path $embedZip)) {
    New-Item -ItemType Directory -Force build\cache | Out-Null
    Invoke-WebRequest -UseBasicParsing -OutFile $embedZip `
        "https://www.python.org/ftp/python/$bundledPython/python-$bundledPython-embed-amd64.zip"
}
$stage = "build\stage"
Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
Expand-Archive $embedZip "$stage\python"

$sig = Get-AuthenticodeSignature "$stage\python\python.exe"
if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Python Software Foundation") {
    throw "python.exe in $embedZip isn't signed by the Python Software Foundation"
}

# The ._pth file is the bundled Python's whole search path; add the libraries folder to it
$pth = (Get-ChildItem "$stage\python\python*._pth").FullName
Set-Content $pth (@(Get-Content $pth) + "Lib\site-packages") -Encoding ascii

# 3. TARS and its libraries, as the Windows builds for the bundled Python version
Remove-Item -Recurse -Force build\wheels -ErrorAction SilentlyContinue
Run $py -m pip wheel --quiet --no-deps --wheel-dir build\wheels .
$wheel = (Get-ChildItem build\wheels\tars-*.whl).FullName
Run $py -m pip install --quiet --no-compile --target "$stage\python\Lib\site-packages" `
    --only-binary=:all: --platform win_amd64 --python-version $pyMinor --implementation cp --abi $abi `
    "$($wheel)[ai]"
Remove-Item -Recurse -Force "$stage\python\Lib\site-packages\bin" -ErrorAction SilentlyContinue

# 4. The two pieces install.ps1 joins into tars.exe: pip's standard launcher stub, and a zip
#    with the startup script
New-Item -ItemType Directory "$stage\launcher" | Out-Null
Copy-Item "$venv\Lib\site-packages\pip\_vendor\distlib\t64.exe" "$stage\launcher\t64.exe"
@'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w") as z:
    z.writestr("__main__.py", "import sys\nfrom tars.cli import main\nsys.exit(main())\n")
'@ | & $py - "$stage\launcher\main.zip"
if ($LASTEXITCODE -ne 0) { throw "Couldn't create launcher\main.zip" }

Set-Content "$stage\tars-version.txt" $version -Encoding ascii
Copy-Item packaging\uninstall.ps1 $stage

# 5. The zip
New-Item -ItemType Directory -Force dist | Out-Null
$zip = "dist\tars-windows-x64.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Run $py -c "import shutil, sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2])" "dist\tars-windows-x64" $stage

# 6. Install the zip into a test folder and check that TARS really starts, so a problem
#    fails the build instead of someone's first launch
$test = "build\test-install"
Remove-Item -Recurse -Force $test -ErrorAction SilentlyContinue
& "$PSScriptRoot\install.ps1" -ZipFile $zip -InstallDir $test -FilesOnly
$null = "q" | & "$test\tars.exe" $env:TEMP     # draws the banner and panels, then quits
if ($LASTEXITCODE -ne 0) { throw "TARS failed to start from the test install" }
Run "$test\python\python.exe" -c "import anthropic"    # AI suggestions have their library

Write-Host "Built $zip"
