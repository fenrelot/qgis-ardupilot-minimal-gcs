<#
Add an idempotent Windows Defender Firewall rule for BlueBoat MAVLink telemetry.

Working directory: repository root.

Run from an elevated Administrator PowerShell when needed.

Examples:
  .\scripts\add_blueboat_firewall_rule.ps1 -CheckOnly
  .\scripts\add_blueboat_firewall_rule.ps1
#>

[CmdletBinding()]
param(
    [int]$MavlinkPort = 14552,
    [string]$RemoteSubnet = "192.168.2.0/24",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuleName = "QGIS ArduBoat BlueBoat MAVLink UDP $MavlinkPort"

Write-Host "Working directory: $RepoRoot"
Write-Host "Firewall rule: $RuleName"
Write-Host "Remote subnet: $RemoteSubnet"

$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Firewall rule already exists."
    return
}

if ($CheckOnly) {
    Write-Host "CheckOnly: would add inbound UDP rule for local port $MavlinkPort from $RemoteSubnet."
    return
}

if (-not (Test-IsAdministrator)) {
    throw "Administrator PowerShell is required to add a Windows Defender Firewall rule."
}

New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol UDP `
    -LocalPort $MavlinkPort `
    -RemoteAddress $RemoteSubnet `
    -Profile Any | Out-Null

Write-Host "Firewall rule added."
