<#
Install or update the ArduBoat QGIS plugin into a QGIS user profile.

Working directory: repository root.

Examples:
  .\scripts\install_qgis_plugin.ps1 -CheckOnly
  .\scripts\install_qgis_plugin.ps1
  .\scripts\install_qgis_plugin.ps1 -Profile default
#>

[CmdletBinding()]
param(
    [string]$Profile = "default",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SourcePlugin = Join-Path $RepoRoot "qgis_plugin\qgis_arduboat"
$QgisProfilesRoot = Join-Path $env:APPDATA "QGIS\QGIS3\profiles"
$ProfileRoot = Join-Path $QgisProfilesRoot $Profile
$PluginsRoot = Join-Path $ProfileRoot "python\plugins"
$DestinationPlugin = Join-Path $PluginsRoot "qgis_arduboat"

function Assert-SafePluginDestination {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullPluginsRoot = [System.IO.Path]::GetFullPath($PluginsRoot)
    if (-not $fullPath.StartsWith($fullPluginsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to install outside the QGIS plugin directory: $fullPath"
    }
    if ((Split-Path -Leaf $fullPath) -ne "qgis_arduboat") {
        throw "Refusing to replace an unexpected directory: $fullPath"
    }
}

if (-not (Test-Path -LiteralPath $SourcePlugin)) {
    throw "Source plugin directory not found: $SourcePlugin"
}

Write-Host "Working directory: $RepoRoot"
Write-Host "QGIS profile: $Profile"
Write-Host "Source plugin: $SourcePlugin"
Write-Host "Destination plugin: $DestinationPlugin"

if ($CheckOnly) {
    if (Test-Path -LiteralPath $DestinationPlugin) {
        Write-Host "CheckOnly: plugin is already installed and would be replaced."
    }
    else {
        Write-Host "CheckOnly: plugin is not installed and would be copied."
    }
    return
}

Assert-SafePluginDestination -Path $DestinationPlugin
New-Item -ItemType Directory -Force -Path $PluginsRoot | Out-Null

if (Test-Path -LiteralPath $DestinationPlugin) {
    Remove-Item -LiteralPath $DestinationPlugin -Recurse -Force
}

Copy-Item -LiteralPath $SourcePlugin -Destination $DestinationPlugin -Recurse -Force

Write-Host ""
Write-Host "Installed QGIS plugin to:"
Write-Host "  $DestinationPlugin"
Write-Host ""
Write-Host "Next: restart QGIS, open Plugins > Manage and Install Plugins, and enable ArduBoat Control."
