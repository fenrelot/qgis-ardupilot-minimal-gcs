<#
Run the local MAVLink-to-HTTP bridge for a Blue Robotics BlueBoat.

Working directory: repository root.

BlueOS MAVLink Endpoints should send a UDP client endpoint to:
  udp://192.168.2.1:14552

Example:
  .\scripts\run_blueboat_bridge.ps1
  .\scripts\run_blueboat_bridge.ps1 -MavlinkPort 14553
#>

[CmdletBinding()]
param(
    [int]$MavlinkPort = 14552,
    [string]$HttpHost = "127.0.0.1",
    [int]$HttpPort = 8765,
    [int]$SourceSystem = 245,
    [double]$HeartbeatTimeout = 3.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Connect = "udpin:0.0.0.0:$MavlinkPort"

Write-Host "Working directory: $RepoRoot"
Write-Host "BlueOS MAVLink endpoint target should be: udp://192.168.2.1:$MavlinkPort"
Write-Host ""

& (Join-Path $PSScriptRoot "run_bridge.ps1") `
    -Connect $Connect `
    -HttpHost $HttpHost `
    -HttpPort $HttpPort `
    -SourceSystem $SourceSystem `
    -HeartbeatTimeout $HeartbeatTimeout
