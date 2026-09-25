# Removes TARS: its folder, its PATH entry and its entry in Settings > Apps.
# Settings > Apps runs this; you can also run it by hand from the TARS folder.
$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
Set-Location ([IO.Path]::GetTempPath())   # a folder can't be deleted while we stand in it

# Files can't be deleted while TARS is running, so check first and leave everything in place
$prefix = $dir.TrimEnd("\") + "\"
$running = @(Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) })
if ($running) {
    Write-Host "TARS is still running. Close it and uninstall again."
    Start-Sleep -Seconds 5
    exit 1
}

$trash = "$dir.removing-" + [guid]::NewGuid()
Rename-Item -Path $dir -NewName (Split-Path $trash -Leaf)

$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
try {
    $path = $key.GetValue("Path", "", "DoNotExpandEnvironmentNames")
    $parts = @($path -split ";" | Where-Object { $_ -and $_ -ne $dir })
    if ($parts.Count -ne @($path -split ";" | Where-Object { $_ }).Count) {
        $key.SetValue("Path", ($parts -join ";"), "ExpandString")
        # Setting any user variable tells open programs (like Explorer) to reload PATH
        [Environment]::SetEnvironmentVariable("TARS_PATH_CHANGED", "1", "User")
        [Environment]::SetEnvironmentVariable("TARS_PATH_CHANGED", $null, "User")
    }
} finally {
    $key.Close()
}

# Only remove the Settings > Apps entry if it belongs to this folder
$apps = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\TARS"
$entry = Get-ItemProperty $apps -ErrorAction SilentlyContinue
if ($entry -and $entry.InstallLocation -eq $dir) {
    Remove-Item $apps -Recurse
}
Remove-Item -Recurse -Force $trash -ErrorAction SilentlyContinue

Write-Host "TARS was uninstalled."
Start-Sleep -Seconds 2
