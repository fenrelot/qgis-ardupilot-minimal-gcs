<#
Check Panasonic Toughbook / BlueBoat network connectivity.

Working directory: repository root.

Examples:
  .\scripts\check_blueboat_network.ps1
  .\scripts\check_blueboat_network.ps1 -ComputerIp 192.168.2.1 -BlueOsIp 192.168.2.2
#>

[CmdletBinding()]
param(
    [string]$ComputerIp = "192.168.2.1",
    [string]$BlueOsIp = "192.168.2.2",
    [string]$BaseStationIp = "192.168.2.3",
    [string]$BoatRouterIp = "192.168.2.4"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )
    $state = if ($Ok) { "ok" } else { "check" }
    Write-Host ("{0}: {1} - {2}" -f $Name, $state, $Detail)
}

function Test-Ping {
    param([string]$Address)
    try {
        return Test-Connection -ComputerName $Address -Count 1 -Quiet -ErrorAction SilentlyContinue
    }
    catch {
        return $false
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Write-Host "Working directory: $RepoRoot"
Write-Host "Expected Toughbook/control IP: $ComputerIp/24"
Write-Host ""

$localMatches = @(
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -eq $ComputerIp } |
        Select-Object -First 1
)

if ($localMatches.Count -gt 0) {
    $match = $localMatches[0]
    Write-Status "Local IP" $true "$($match.IPAddress) on interface index $($match.InterfaceIndex)"
}
else {
    Write-Status "Local IP" $false "No local adapter currently has $ComputerIp. Set the BaseStation USB Ethernet adapter IPv4 address to $ComputerIp with subnet mask 255.255.255.0."
}

Write-Status "BlueOS ping $BlueOsIp" (Test-Ping $BlueOsIp) "BlueOS should answer when the BlueBoat and BaseStation are powered and linked."
Write-Status "BaseStation ping $BaseStationIp" (Test-Ping $BaseStationIp) "BaseStation router address."
Write-Status "Boat router ping $BoatRouterIp" (Test-Ping $BoatRouterIp) "BlueBoat router address; may fail if the radio link is down."

try {
    $blueOsHttp = Invoke-WebRequest -Uri "http://$BlueOsIp" -UseBasicParsing -TimeoutSec 3 -Method Head
    Write-Status "BlueOS HTTP" $true "HTTP $($blueOsHttp.StatusCode) from http://$BlueOsIp"
}
catch {
    Write-Status "BlueOS HTTP" $false "Could not open http://$BlueOsIp. Try http://blueos.local in a browser and confirm the BaseStation link."
}

Write-Host ""
Write-Host "For QGIS bridge telemetry, configure BlueOS MAVLink Endpoints with a UDP client endpoint to:"
Write-Host "  udp://$ComputerIp`:14552"
