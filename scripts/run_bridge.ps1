<#
Run the local MAVLink-to-HTTP bridge.

Working directory: repository root.

Example:
  .\scripts\run_bridge.ps1
  .\scripts\run_bridge.ps1 -Connect udpin:0.0.0.0:14551 -HttpPort 8765
#>

[CmdletBinding()]
param(
    [string]$Connect = "udpin:0.0.0.0:14551",
    [string]$HttpHost = "127.0.0.1",
    [int]$HttpPort = 8765,
    [int]$SourceSystem = 245,
    [double]$HeartbeatTimeout = 3.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Project virtual environment Python was not found at $Python. Run .\scripts\bootstrap_windows.ps1 -CreateVenv first."
}

Write-Host "Working directory: $RepoRoot"
Write-Host "Bridge API: http://$HttpHost`:$HttpPort"
Write-Host "MAVLink: $Connect"

& $Python -m bridge.main `
    --connect $Connect `
    --http-host $HttpHost `
    --http-port $HttpPort `
    --source-system $SourceSystem `
    --heartbeat-timeout $HeartbeatTimeout
