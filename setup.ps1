<#
.SYNOPSIS
Automated environment setup for WatchWise.
.DESCRIPTION
Installs Python 3.11 and Android Platform Tools via winget without user interaction, then refreshes the session's PATH.
#>

$ErrorActionPreference = 'Stop'

Write-Host "Installing Python 3.11..."
winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements

Write-Host "Installing Android Platform Tools (ADB)..."
winget install --id Google.PlatformTools --exact --source winget --accept-package-agreements --accept-source-agreements

Write-Host "Refreshing environment variables for the current session..."
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Verifying installations..."
python --version
adb --version

Write-Host "Environment is ready for WatchWise."