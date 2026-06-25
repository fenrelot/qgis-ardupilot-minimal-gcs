<#
Start QGIS LTR with this repository's plugin directory on QGIS_PLUGINPATH.

Working directory: repository root.

Example:
  .\scripts\run_qgis_plugin_dev.ps1
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PluginPath = Join-Path $RepoRoot "qgis_plugin"
$QgisBat = "C:\Program Files\QGIS 3.44.11\bin\qgis-ltr.bat"

if (-not (Test-Path -LiteralPath $QgisBat)) {
    throw "QGIS LTR launcher was not found at $QgisBat"
}

$env:QGIS_PLUGINPATH = $PluginPath
Write-Host "Working directory: $RepoRoot"
Write-Host "QGIS_PLUGINPATH: $PluginPath"
& $QgisBat
