# Installs TARS for the current user, with its own copy of Python.
#
# The one-line install (from PowerShell or cmd):
#   powershell -ExecutionPolicy Bypass -c "irm https://github.com/davidgeamanu/Tars-CLI/releases/latest/download/install.ps1 | iex"
#
# From a zip you built with packaging\build.ps1:
#   powershell -ExecutionPolicy Bypass -File packaging\install.ps1 -ZipFile dist\tars-windows-x64.zip
#
# TARS runs on python.org's signed python.exe, so Windows Smart App Control allows it.
# The script never calls 'exit', because 'irm | iex' runs it inside your own window.
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\TARS",
    [string]$ZipFile,       # install from this zip instead of downloading the latest release
    [switch]$FilesOnly      # only copy the files: don't add TARS to PATH or to Settings > Apps
)

function Install-Tars {
    param([string]$InstallDir, [string]$ZipFile, [bool]$FilesOnly)

    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"   # the progress bar makes downloads very slow in Windows PowerShell
    $releaseZip = "https://github.com/davidgeamanu/Tars-CLI/releases/latest/download/tars-windows-x64.zip"
    $InstallDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($InstallDir)

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Warning "Git wasn't found. TARS needs it: https://git-scm.com/download/win"
    }

    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("tars-install-" + [guid]::NewGuid())
    New-Item -ItemType Directory $tmp | Out-Null
    try {
        if ($ZipFile) {
            $ZipFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ZipFile)
        } else {
            [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            $ZipFile = Join-Path $tmp "tars-windows-x64.zip"
            Write-Host "Downloading TARS..."
            Invoke-WebRequest -UseBasicParsing -Uri $releaseZip -OutFile $ZipFile
        }

        # Leftovers from an update or uninstall that was interrupted
        Get-Item "$InstallDir.old-*", "$InstallDir.removing-*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

        # Move an earlier install out of the way, so it can be put back if this one fails.
        # Only ever touch a folder that TARS created.
        $old = $null
        if (Test-Path $InstallDir) {
            $isTars = Test-Path (Join-Path $InstallDir "tars-version.txt")
            $isEmpty = -not (Get-ChildItem -Force $InstallDir)
            if (-not ($isTars -or $isEmpty)) {
                throw "$InstallDir already exists and isn't a TARS install. Choose another folder with -InstallDir."
            }
            # Windows lets a folder be renamed while a program in it is running, and then the
            # old files can't be deleted, so check for a running TARS first
            if (Get-ProcessesIn $InstallDir) {
                throw "TARS is running from $InstallDir. Close it and run the install again."
            }
            $old = "$InstallDir.old-" + [guid]::NewGuid()
            Rename-Item -Path $InstallDir -NewName (Split-Path $old -Leaf)
        }

        Write-Host "Installing into $InstallDir"
        # .NET's unzip rather than Expand-Archive: about 5x faster, and Expand-Archive ignores
        # $ProgressPreference set inside a function, so it draws a progress bar
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($ZipFile, $InstallDir)
        $version = (Get-Content (Join-Path $InstallDir "tars-version.txt")).Trim()

        # tars.exe is pip's standard launcher stub, followed by a line naming the python.exe to
        # run and a zip holding the startup script. It's built here because it has to contain
        # the full path of this install.
        $python = Join-Path $InstallDir "python\python.exe"
        $stub = [IO.File]::ReadAllBytes((Join-Path $InstallDir "launcher\t64.exe"))
        $shebang = [Text.Encoding]::UTF8.GetBytes("#!`"$python`"`n")
        $main = [IO.File]::ReadAllBytes((Join-Path $InstallDir "launcher\main.zip"))
        [IO.File]::WriteAllBytes((Join-Path $InstallDir "tars.exe"), [byte[]]($stub + $shebang + $main))

        $reported = & (Join-Path $InstallDir "tars.exe") --version
        if ($LASTEXITCODE -ne 0 -or $reported -ne "tars $version") {
            throw "The installed tars.exe didn't start (it printed '$reported')."
        }

        if ($old) { Remove-Item -Recurse -Force $old -ErrorAction SilentlyContinue }

        if (-not $FilesOnly) {
            Add-TarsToPath $InstallDir
            Register-TarsUninstaller $InstallDir $version
        }

        Write-Host ""
        Write-Host "TARS $version is installed. Open a new terminal and type: tars"
    } catch {
        # Put the earlier install back if the new one didn't make it
        if ($old -and (Test-Path $old)) {
            Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
            Rename-Item -Path $old -NewName (Split-Path $InstallDir -Leaf) -ErrorAction SilentlyContinue
        }
        throw
    } finally {
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    }
}

function Get-ProcessesIn([string]$Dir) {
    $prefix = $Dir.TrimEnd("\") + "\"
    @(Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) })
}

function Add-TarsToPath([string]$Dir) {
    # Edit the registry directly: [Environment]::SetEnvironmentVariable would turn PATH into a
    # plain string and break entries like %USERPROFILE%\bin.
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
    try {
        $path = $key.GetValue("Path", "", "DoNotExpandEnvironmentNames")
        $parts = @($path -split ";" | Where-Object { $_ })
        if ($parts -notcontains $Dir) {
            $key.SetValue("Path", (($parts + $Dir) -join ";"), "ExpandString")
            # Setting any user variable tells open programs (like Explorer) to reload PATH
            [Environment]::SetEnvironmentVariable("TARS_PATH_CHANGED", "1", "User")
            [Environment]::SetEnvironmentVariable("TARS_PATH_CHANGED", $null, "User")
        }
    } finally {
        $key.Close()
    }
}

function Register-TarsUninstaller([string]$Dir, [string]$Version) {
    $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\TARS"
    $sizeKB = [int]((Get-ChildItem -Recurse -File $Dir | Measure-Object -Sum Length).Sum / 1KB)
    New-Item -Path $key -Force | Out-Null
    $values = [ordered]@{
        DisplayName     = "TARS"
        DisplayVersion  = $Version
        Publisher       = "David Geamanu"
        InstallLocation = $Dir
        URLInfoAbout    = "https://github.com/davidgeamanu/Tars-CLI"
        UninstallString = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Dir\uninstall.ps1`""
    }
    foreach ($name in $values.Keys) {
        New-ItemProperty -Path $key -Name $name -Value $values[$name] -PropertyType String -Force | Out-Null
    }
    foreach ($name in "NoModify", "NoRepair") {
        New-ItemProperty -Path $key -Name $name -Value 1 -PropertyType DWord -Force | Out-Null
    }
    New-ItemProperty -Path $key -Name "EstimatedSize" -Value $sizeKB -PropertyType DWord -Force | Out-Null
}

Install-Tars -InstallDir $InstallDir -ZipFile $ZipFile -FilesOnly $FilesOnly.IsPresent
