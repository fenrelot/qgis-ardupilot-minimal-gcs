<# 
Windows environment checker and optional installer for the QGIS + ArduPilot
operator-map prototype.

Working directory: repository root.

Examples:
  .\scripts\bootstrap_windows.ps1 -CheckOnly
  .\scripts\bootstrap_windows.ps1 -CreateVenv
  .\scripts\bootstrap_windows.ps1 -InstallTools -InstallQgis
#>

[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$InstallTools,
    [switch]$InstallWinget,
    [switch]$InstallQgis,
    [switch]$InstallMissionPlanner,
    [switch]$InstallMavproxy,
    [switch]$InstallCodexCli,
    [switch]$InstallWslSitl,
    [switch]$CreateVenv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DownloadsDir = Join-Path $env:TEMP "qgisarduboat-installers"
$MissionPlannerUrl = "https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi"
$MavproxyUrl = "https://firmware.ardupilot.org/Tools/MAVProxy/MAVProxySetup-latest.exe"
$WingetReleaseBaseUrl = "https://github.com/microsoft/winget-cli/releases/download/v1.28.240"
$WingetMsixUrl = "$WingetReleaseBaseUrl/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
$WingetDependenciesUrl = "$WingetReleaseBaseUrl/DesktopAppInstaller_Dependencies.zip"
$WingetLicenseUrl = "$WingetReleaseBaseUrl/e53e159d00e04f729cc2180cffd1c02e_License1.xml"
$GitInstallerUrl = "https://github.com/git-for-windows/git/releases/download/v2.54.0.windows.1/Git-2.54.0-64-bit.exe"
$PythonInstallerUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
$QgisLtrMsiUrl = "https://download.qgis.org/downloads/QGIS-OSGeo4W-3.44.11-1.msi"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-Tool {
    param([string]$Name)
    return Get-Command $Name -ErrorAction SilentlyContinue
}

function Get-CommandText {
    param([object]$Command)
    if ($null -eq $Command) {
        return ""
    }
    if ($Command.Source) {
        return $Command.Source
    }
    return $Command.Name
}

function Test-ToolRuns {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    $command = Get-Tool $Name
    if (-not $command) {
        return $false
    }

    try {
        & (Get-CommandText $command) @Arguments 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-WingetUsable {
    return (Test-ToolRuns "winget" @("--version"))
}

function Test-PythonUsable {
    if (Test-ToolRuns "py" @("--version")) {
        return $true
    }
    return (Test-ToolRuns "python" @("--version"))
}

function Test-PipUsable {
    if (Test-ToolRuns "pip" @("--version")) {
        return $true
    }

    $python = Get-UsablePythonCommand
    if ($python) {
        try {
            & $python -m pip --version 1>$null 2>$null
            return ($LASTEXITCODE -eq 0)
        }
        catch {
            return $false
        }
    }

    return $false
}

function Get-UsablePythonCommand {
    $py = Get-Tool "py"
    if ($py) {
        try {
            & (Get-CommandText $py) -3 --version 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (Get-CommandText $py)
            }
        }
        catch {
        }
    }

    $python = Get-Tool "python"
    if ($python) {
        try {
            & (Get-CommandText $python) --version 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (Get-CommandText $python)
            }
        }
        catch {
        }
    }

    return $null
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Add-PathEntryIfExists {
    param([string]$PathEntry)

    if (-not (Test-Path -LiteralPath $PathEntry)) {
        return
    }

    $parts = @($env:PATH -split ";" | Where-Object { $_ -and ($_ -ine $PathEntry) })
    $env:PATH = "$PathEntry;$($parts -join ";")"
}

function Add-KnownToolPaths {
    Add-PathEntryIfExists (Join-Path $env:ProgramFiles "Git\cmd")
    Add-PathEntryIfExists (Join-Path $env:ProgramFiles "Git\bin")
    Add-PathEntryIfExists (Join-Path $env:LOCALAPPDATA "Programs\Git\cmd")
    Add-PathEntryIfExists (Join-Path $env:LOCALAPPDATA "Programs\Git\bin")
    Add-PathEntryIfExists (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312")
    Add-PathEntryIfExists (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\Scripts")
    Add-PathEntryIfExists (Join-Path $env:LOCALAPPDATA "Programs\Python\Launcher")
    Add-PathEntryIfExists "C:\Program Files (x86)\MAVProxy"
}

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    $normalized = $WindowsPath -replace "\\", "/"
    if ($normalized -match "^([A-Za-z]):/(.*)$") {
        $drive = $Matches[1].ToLowerInvariant()
        $tail = $Matches[2]
        return "/mnt/$drive/$tail"
    }

    return $null
}

function Get-UninstallEntries {
    $roots = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    foreach ($root in $roots) {
        Get-ItemProperty -Path $root -ErrorAction SilentlyContinue |
            Where-Object { $_.PSObject.Properties["DisplayName"] -and $_.DisplayName } |
            Select-Object DisplayName, DisplayVersion, InstallLocation, Publisher
    }
}

function Find-UninstallEntry {
    param([string[]]$Patterns)

    $entries = Get-UninstallEntries
    foreach ($pattern in $Patterns) {
        $match = $entries | Where-Object { $_.DisplayName -like $pattern } | Select-Object -First 1
        if ($match) {
            return $match
        }
    }

    return $null
}

function Find-PathMatch {
    param([string[]]$Patterns)

    foreach ($pattern in $Patterns) {
        $matches = Get-Item -Path $pattern -ErrorAction SilentlyContinue
        foreach ($match in $matches) {
            if ($match) {
                return $match.FullName
            }
        }
    }

    return $null
}

function Get-VersionOutput {
    param(
        [object]$Command,
        [string[]]$Arguments
    )

    if ($null -eq $Command) {
        return ""
    }

    try {
        $path = Get-CommandText $Command
        $output = & $path @Arguments 2>&1 | Select-Object -First 1
        if ($LASTEXITCODE -ne 0 -and -not $output) {
            return ""
        }
        return (($output | Out-String).Trim())
    }
    catch {
        return ""
    }
}

function New-CheckResult {
    param(
        [string]$Name,
        [bool]$Found,
        [string]$Detail = ""
    )

    [pscustomobject]@{
        Name = $Name
        Found = $Found
        Detail = $Detail
    }
}

function Get-QgisStatus {
    $path = Find-PathMatch @(
        "C:\Program Files\QGIS 3.44*",
        "C:\Program Files\QGIS 3.*",
        "C:\OSGeo4W\apps\qgis-ltr",
        "C:\OSGeo4W64\apps\qgis-ltr"
    )
    if ($path) {
        return New-CheckResult "QGIS LTR" $true $path
    }

    $entry = Find-UninstallEntry @("QGIS*LTR*", "QGIS 3.44*", "QGIS 3.*")
    if ($entry) {
        $detail = $entry.DisplayName
        if ($entry.DisplayVersion) {
            $detail = "$detail $($entry.DisplayVersion)"
        }
        return New-CheckResult "QGIS LTR" $true $detail
    }

    return New-CheckResult "QGIS LTR" $false "missing"
}

function Get-MissionPlannerStatus {
    $path = Find-PathMatch @(
        "$env:LOCALAPPDATA\Mission Planner\MissionPlanner.exe",
        "C:\Program Files\Mission Planner\MissionPlanner.exe",
        "C:\Program Files (x86)\Mission Planner\MissionPlanner.exe"
    )
    if ($path) {
        return New-CheckResult "Mission Planner" $true $path
    }

    $entry = Find-UninstallEntry @("*Mission Planner*")
    if ($entry) {
        $detail = $entry.DisplayName
        if ($entry.DisplayVersion) {
            $detail = "$detail $($entry.DisplayVersion)"
        }
        return New-CheckResult "Mission Planner" $true $detail
    }

    return New-CheckResult "Mission Planner" $false "missing"
}

function Get-WslUbuntuStatus {
    $wsl = Get-Tool "wsl.exe"
    if (-not $wsl) {
        return New-CheckResult "WSL Ubuntu" $false "wsl.exe missing"
    }

    try {
        $distros = & (Get-CommandText $wsl) --list 2>&1
        $exitCode = $LASTEXITCODE
        $text = (($distros | Out-String) -replace "`0", "")
        if ($exitCode -ne 0) {
            if ($text -match "Access is denied") {
                return New-CheckResult "WSL Ubuntu" $false "WSL found; distro listing failed with Access is denied. On this VM, run WSL commands from elevated PowerShell."
            }
            return New-CheckResult "WSL Ubuntu" $false "WSL found; distro listing failed. Install Ubuntu with: wsl --install -d Ubuntu"
        }
        $ubuntu = ($text -split "(`r`n|`n|`r)") | Where-Object { $_.Trim() -match "^Ubuntu" } | Select-Object -First 1
        if ($ubuntu) {
            return New-CheckResult "WSL Ubuntu" $true ($ubuntu.Trim())
        }
        return New-CheckResult "WSL Ubuntu" $false "WSL found; Ubuntu distro missing or distro listing unavailable"
    }
    catch {
        return New-CheckResult "WSL Ubuntu" $false "unable to list WSL distros: $($_.Exception.Message)"
    }
}

function Get-EnvironmentReport {
    $git = Get-Tool "git"
    $python = Get-Tool "python"
    $py = Get-Tool "py"
    $pip = Get-Tool "pip"
    $mavproxy = Get-Tool "mavproxy.exe"
    $codex = Get-Tool "codex"
    $wsl = Get-Tool "wsl.exe"
    $winget = Get-Tool "winget"
    $code = Get-Tool "code"

    $results = @()
    $gitDetail = "missing"
    if ($git) { $gitDetail = Get-VersionOutput $git @("--version") }
    $results += New-CheckResult "Git" ($null -ne $git) $gitDetail

    $pythonFound = Test-PythonUsable
    $pythonDetail = "missing"
    if ($python) {
        $pythonDetail = Get-VersionOutput $python @("--version")
    }
    elseif ($py) {
        $pythonDetail = Get-VersionOutput $py @("--version")
    }
    if (($python -or $py) -and -not $pythonFound) {
        $pythonDetail = "present but not runnable"
    }
    $results += New-CheckResult "Python" $pythonFound $pythonDetail

    $pipDetail = "missing"
    if ($pip) { $pipDetail = Get-VersionOutput $pip @("--version") }
    $pipFound = Test-PipUsable
    if ($pip -and -not $pipFound) {
        $pipDetail = "present but not runnable"
    }
    $results += New-CheckResult "pip" $pipFound $pipDetail

    $results += Get-QgisStatus
    $results += Get-MissionPlannerStatus

    $mavproxyDetail = "missing"
    if ($mavproxy) { $mavproxyDetail = Get-CommandText $mavproxy }
    $results += New-CheckResult "MAVProxy" ($null -ne $mavproxy) $mavproxyDetail

    $results += Get-WslUbuntuStatus

    $codexDetail = "missing"
    if ($codex) { $codexDetail = Get-CommandText $codex }
    $results += New-CheckResult "Codex CLI" ($null -ne $codex) $codexDetail

    $wingetDetail = "missing"
    if ($winget) { $wingetDetail = Get-VersionOutput $winget @("--version") }
    $wingetUsable = Test-WingetUsable
    if ($winget -and -not $wingetUsable) {
        $wingetDetail = "present but not runnable"
    }
    $results += New-CheckResult "winget" $wingetUsable $wingetDetail

    $codeDetail = "missing"
    if ($code) { $codeDetail = Get-CommandText $code }
    $results += New-CheckResult "VS Code" ($null -ne $code) $codeDetail

    return $results
}

function Write-EnvironmentReport {
    param([object[]]$Results)

    Write-Host ""
    Write-Host "Environment report"
    foreach ($item in $Results) {
        $state = if ($item.Found) { "found" } else { "missing" }
        if ([string]::IsNullOrWhiteSpace($item.Detail) -or $item.Detail -eq $state) {
            Write-Host ("{0}: {1}" -f $item.Name, $state)
        }
        else {
            Write-Host ("{0}: {1} {2}" -f $item.Name, $state, $item.Detail)
        }
    }
}

function Test-WingetPackageId {
    param([string]$PackageId)

    $winget = Get-Tool "winget"
    if (-not $winget) {
        return $false
    }

    try {
        $output = & (Get-CommandText $winget) search --id $PackageId --exact --source winget --accept-source-agreements --disable-interactivity 2>&1
        return ($LASTEXITCODE -eq 0 -and (($output | Out-String) -match [regex]::Escape($PackageId)))
    }
    catch {
        return $false
    }
}

function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$DisplayName
    )

    if ($CheckOnly) {
        Write-Host "CheckOnly: would verify and install $DisplayName with winget package ID $PackageId."
        return
    }

    if (-not (Get-Tool "winget")) {
        Write-Warning "winget is missing. Install $DisplayName manually."
        return
    }

    if (-not (Test-WingetPackageId $PackageId)) {
        Write-Warning "winget package ID $PackageId was not confirmed by winget search. Install $DisplayName manually."
        return
    }

    Write-Host "Installing $DisplayName with winget package ID $PackageId..."
    & winget install --id $PackageId --exact --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
}

function Install-GitDirect {
    if (Get-Tool "git") {
        Write-Host "Git already installed."
        return
    }

    $installer = Join-Path $DownloadsDir "Git-2.54.0-64-bit.exe"
    Download-File $GitInstallerUrl $installer | Out-Null
    if ($CheckOnly) { return }
    if (-not (Test-Path -LiteralPath $installer)) {
        Write-Warning "Git installer was not downloaded. Manual URL: $GitInstallerUrl"
        return
    }

    Write-Host "Installing Git for Windows for the current user..."
    Start-Process -FilePath $installer -ArgumentList @("/VERYSILENT", "/NORESTART", "/NOCANCEL") -Wait
    Add-KnownToolPaths
}

function Install-PythonDirect {
    if (Test-PythonUsable -and Test-PipUsable) {
        Write-Host "Python and pip already installed."
        return
    }

    $installer = Join-Path $DownloadsDir "python-3.12.10-amd64.exe"
    Download-File $PythonInstallerUrl $installer | Out-Null
    if ($CheckOnly) { return }
    if (-not (Test-Path -LiteralPath $installer)) {
        Write-Warning "Python installer was not downloaded. Manual URL: $PythonInstallerUrl"
        return
    }

    Write-Host "Installing Python 3.12 for the current user with pip..."
    Start-Process -FilePath $installer -ArgumentList @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0"
    ) -Wait

    $userPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"
    $userScripts = Join-Path $userPython "Scripts"
    if (Test-Path -LiteralPath (Join-Path $userPython "python.exe")) {
        $env:PATH = "$userPython;$userScripts;$env:PATH"
    }
}

function Install-QgisDirect {
    if ((Get-QgisStatus).Found) {
        Write-Host "QGIS already installed."
        return
    }

    $installer = Join-Path $DownloadsDir "QGIS-OSGeo4W-3.44.11-1.msi"
    Download-File $QgisLtrMsiUrl $installer | Out-Null
    if ($CheckOnly) { return }
    if (-not (Test-Path -LiteralPath $installer)) {
        Write-Warning "QGIS LTR installer was not downloaded. Manual URL: $QgisLtrMsiUrl"
        return
    }

    Write-Host "Starting QGIS LTR MSI installer. It may require administrator approval."
    Start-Process msiexec.exe -ArgumentList @("/i", "`"$installer`"", "/passive", "/norestart") -Wait
}

function Install-WingetManager {
    if (Test-WingetUsable) {
        Write-Host "winget is already installed."
        return
    }
    elseif (Get-Tool "winget") {
        Write-Warning "winget is present but not runnable. Reinstalling from the official MSIX release."
    }

    if ($CheckOnly) {
        Write-Host "CheckOnly: would register App Installer if present, then use Microsoft.WinGet.Client Repair-WinGetPackageManager if needed."
        return
    }

    try {
        Write-Host "Trying App Installer registration for the current user..."
        Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe
    }
    catch {
        Write-Warning "App Installer registration was not available: $($_.Exception.Message)"
    }

    if (Test-WingetUsable) {
        Write-Host "winget is now available after App Installer registration."
        return
    }

    try {
        Write-Host "Installing Microsoft.WinGet.Client from PowerShell Gallery..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        if (-not (Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue)) {
            Register-PSRepository -Default
        }
        Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
        Install-PackageProvider -Name NuGet -Force -Scope CurrentUser | Out-Null
        Install-Module -Name Microsoft.WinGet.Client -Force -AllowClobber -Repository PSGallery -Scope CurrentUser
        Import-Module Microsoft.WinGet.Client -Force

        Write-Host "Bootstrapping winget with Repair-WinGetPackageManager..."
        $repair = Get-Command Repair-WinGetPackageManager -ErrorAction Stop
        $parameters = @{}
        if (Test-IsAdministrator) {
            $parameters["AllUsers"] = $true
        }
        & $repair @parameters
    }
    catch {
        Write-Warning "Microsoft.WinGet.Client bootstrap failed: $($_.Exception.Message)"
        Install-WingetFromGitHubRelease
    }

    if (-not (Test-WingetUsable)) {
        if (Get-Tool "winget") {
            Write-Warning "winget is present but not runnable. On this LTSC image it likely needs Administrator provisioning with the official license XML; continue using direct installers."
            return
        }
        throw "winget bootstrap completed but winget is still not on PATH. Restart PowerShell and rerun .\scripts\bootstrap_windows.ps1 -CheckOnly."
    }
}

function Download-File {
    param(
        [string]$Url,
        [string]$OutFile
    )

    if ($CheckOnly) {
        Write-Host "CheckOnly: would download $Url to $OutFile."
        return $false
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null
    $oldProgressPreference = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile
    }
    finally {
        $ProgressPreference = $oldProgressPreference
    }
    return (Test-Path -LiteralPath $OutFile)
}

function Install-WingetFromGitHubRelease {
    $wingetDir = Join-Path $DownloadsDir "winget"
    $dependencyZip = Join-Path $wingetDir "DesktopAppInstaller_Dependencies.zip"
    $dependencyDir = Join-Path $wingetDir "DesktopAppInstaller_Dependencies"
    $msixBundle = Join-Path $wingetDir "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
    $licensePath = Join-Path $wingetDir "e53e159d00e04f729cc2180cffd1c02e_License1.xml"

    Write-Host "Downloading winget MSIX bundle from the official Microsoft winget-cli release..."
    Download-File $WingetDependenciesUrl $dependencyZip | Out-Null
    Download-File $WingetMsixUrl $msixBundle | Out-Null
    Download-File $WingetLicenseUrl $licensePath | Out-Null

    if (-not (Test-Path -LiteralPath $dependencyZip) -or -not (Test-Path -LiteralPath $msixBundle) -or -not (Test-Path -LiteralPath $licensePath)) {
        throw "winget MSIX bundle, dependency zip, or license file was not downloaded."
    }

    if (Test-Path -LiteralPath $dependencyDir) {
        Remove-Item -LiteralPath $dependencyDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $dependencyDir | Out-Null
    Expand-Archive -LiteralPath $dependencyZip -DestinationPath $dependencyDir -Force

    $dependencyFiles = @(Get-ChildItem -LiteralPath $dependencyDir -Recurse -File |
        Where-Object { $_.Extension -in ".appx", ".msix", ".appxbundle", ".msixbundle" } |
        Where-Object { $_.Name -match "x64|neutral" } |
        Select-Object -ExpandProperty FullName)

    $quotedDeps = $dependencyFiles | ForEach-Object { "'$_'" }
    $dependencyArg = ""
    if ($quotedDeps.Count -gt 0) {
        $dependencyArg = " -DependencyPath @($($quotedDeps -join ","))"
    }

    if (Test-IsAdministrator) {
        $dependencyProvisionArg = ""
        if ($quotedDeps.Count -gt 0) {
            $dependencyProvisionArg = " -DependencyPackagePath @($($quotedDeps -join ","))"
        }
        $installCommand = "Add-AppxProvisionedPackage -Online -PackagePath '$msixBundle' -LicensePath '$licensePath'$dependencyProvisionArg"
        Write-Host "Provisioning winget with Windows PowerShell Add-AppxProvisionedPackage..."
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $installCommand
    }
    else {
        $installCommand = "Add-AppxPackage -Path '$msixBundle'$dependencyArg"
        Write-Host "Installing winget with Windows PowerShell Add-AppxPackage..."
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $installCommand
    }

    if (-not (Get-Tool "winget")) {
        $windowsApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
        $candidate = Join-Path $windowsApps "winget.exe"
        if (Test-Path -LiteralPath $candidate) {
            $env:PATH = "$windowsApps;$env:PATH"
        }
    }
}

function Install-MissionPlanner {
    $status = Get-MissionPlannerStatus
    if ($status.Found) {
        Write-Host "Mission Planner already installed: $($status.Detail)"
        return
    }

    $installer = Join-Path $DownloadsDir "MissionPlanner-latest.msi"
    $downloaded = Download-File $MissionPlannerUrl $installer
    if ($CheckOnly) {
        return
    }

    if (-not $downloaded -or -not (Test-Path -LiteralPath $installer)) {
        Write-Warning "Mission Planner installer was not found after download. Manual URL: $MissionPlannerUrl"
        return
    }

    Write-Host "Starting Mission Planner MSI installer. Administrator approval may be requested by Windows."
    Start-Process msiexec.exe -ArgumentList @("/i", "`"$installer`"", "/passive", "/norestart") -Wait
}

function Install-Mavproxy {
    $mavproxy = Get-Tool "mavproxy.exe"
    if ($mavproxy) {
        Write-Host "MAVProxy already installed: $(Get-CommandText $mavproxy)"
        return
    }

    $installer = Join-Path $DownloadsDir "MAVProxySetup-latest.exe"
    $downloaded = Download-File $MavproxyUrl $installer
    if ($CheckOnly) {
        return
    }

    if ($downloaded -and (Test-Path -LiteralPath $installer)) {
        Write-Host "Starting MAVProxy installer. Administrator approval may be requested by Windows."
        Start-Process -FilePath $installer -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait
        return
    }

    $python = Get-Tool "python"
    if ($python) {
        Write-Warning "Official MAVProxy installer download failed. Falling back to user-level pip install."
        & (Get-CommandText $python) -m pip install --user --upgrade mavproxy pymavlink
        return
    }

    Write-Warning "MAVProxy installer download failed and Python is missing. Manual URL: $MavproxyUrl"
}

function Invoke-CreateVenv {
    $venvPath = Join-Path $RepoRoot ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"

    if ($CheckOnly) {
        Write-Host "CheckOnly: would create/update .venv and install requirements-dev.txt."
        return
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        $py = Get-Tool "py"
        $python = Get-Tool "python"
        if ($py) {
            & (Get-CommandText $py) -3 -m venv $venvPath
        }
        elseif ($python) {
            & (Get-CommandText $python) -m venv $venvPath
        }
        else {
            throw "Python is missing. Install Python first, then rerun with -CreateVenv."
        }
    }

    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $RepoRoot "requirements-dev.txt")
}

function Invoke-WslSitlBootstrap {
    $wsl = Get-Tool "wsl.exe"
    if (-not $wsl) {
        if ($CheckOnly) {
            Write-Host "CheckOnly: WSL is missing; would run 'wsl --install -d Ubuntu' if requested outside check-only mode."
            return
        }
        Write-Warning "WSL is missing. Run an elevated PowerShell and install Ubuntu with: wsl --install -d Ubuntu"
        return
    }

    $wslRepo = ConvertTo-WslPath $RepoRoot
    if (-not $wslRepo) {
        Write-Warning "Could not convert repository path to a WSL /mnt path: $RepoRoot"
        return
    }

    $distro = "Ubuntu-22.04"
    $userScript = "$wslRepo/scripts/bootstrap_wsl_user.sh"
    $command = "cd '$wslRepo' && bash scripts/bootstrap_wsl_ardupilot.sh"
    if ($CheckOnly) {
        Write-Host "CheckOnly: would run in WSL: wsl -d $distro -u root -- bash $userScript"
        Write-Host "CheckOnly: would run in WSL: wsl -d $distro -- bash -lc `"$command`""
        return
    }

    & (Get-CommandText $wsl) -d $distro -u root -- bash $userScript
    & (Get-CommandText $wsl) -d $distro -- bash -lc $command
}

Add-KnownToolPaths

Write-Host "Working directory: $RepoRoot"
if (Test-IsAdministrator) {
    Write-Host "Administrator: yes"
}
else {
    Write-Host "Administrator: no"
}

$initialReport = Get-EnvironmentReport
Write-EnvironmentReport $initialReport

$requestedActions = (
    $InstallTools -or
    $InstallWinget -or
    $InstallQgis -or
    $InstallMissionPlanner -or
    $InstallMavproxy -or
    $InstallCodexCli -or
    $InstallWslSitl -or
    $CreateVenv
)

if ($InstallWinget) {
    Write-Step "Installing winget"
    Install-WingetManager
}

if ($InstallTools) {
    Write-Step "Installing common tools"
    if (-not (Get-Tool "git")) {
        if (Test-WingetUsable) {
            Install-WingetPackage "Git.Git" "Git"
        }
        else {
            Install-GitDirect
        }
    }
    if (-not (Test-PythonUsable) -or -not (Test-PipUsable)) {
        if (Test-WingetUsable) {
            Install-WingetPackage "Python.Python.3.12" "Python 3.12"
        }
        else {
            Install-PythonDirect
        }
    }
    if (-not (Get-Tool "code")) {
        if (Test-WingetUsable) {
            Install-WingetPackage "Microsoft.VisualStudioCode" "Visual Studio Code"
        }
        else {
            Write-Warning "VS Code is missing and winget is not usable. Skipping optional VS Code install."
        }
    }
}

if ($InstallQgis) {
    Write-Step "Installing QGIS LTR"
    if ((Get-QgisStatus).Found) {
        Write-Host "QGIS already installed."
    }
    elseif (Test-WingetUsable) {
        Install-WingetPackage "OSGeo.QGIS_LTR" "QGIS LTR"
    }
    else {
        Install-QgisDirect
    }
}

if ($InstallMissionPlanner) {
    Write-Step "Installing Mission Planner"
    Install-MissionPlanner
}

if ($InstallMavproxy) {
    Write-Step "Installing MAVProxy"
    Install-Mavproxy
}

if ($InstallCodexCli) {
    Write-Step "Checking Codex CLI"
    if (Get-Tool "codex") {
        Write-Host "Codex CLI is already installed. To update it, run: codex update"
    }
    else {
        Write-Warning "Codex CLI is missing. Use the official Codex download flow from https://chatgpt.com/codex/ or the current OpenAI developer documentation. No unattended installer command is embedded here."
    }
}

if ($InstallWslSitl) {
    Write-Step "Bootstrapping ArduPilot SITL in WSL"
    Invoke-WslSitlBootstrap
}

if ($CreateVenv) {
    Write-Step "Creating Python virtual environment"
    Invoke-CreateVenv
}

if ($requestedActions -and -not $CheckOnly) {
    $finalReport = Get-EnvironmentReport
    Write-EnvironmentReport $finalReport
}

Write-Host ""
Write-Host "Next commands from repository root:"
Write-Host "  .\scripts\bootstrap_windows.ps1 -CreateVenv"
$nextWslRepo = ConvertTo-WslPath $RepoRoot
if ($nextWslRepo) {
    Write-Host "  wsl -d Ubuntu-22.04 -- bash $nextWslRepo/scripts/check_wsl_sitl.sh"
    Write-Host "  wsl -d Ubuntu-22.04 -- bash $nextWslRepo/scripts/build_sitl_rover_wsl.sh"
    Write-Host "  wsl -d Ubuntu-22.04 -- bash -lc 'cd $nextWslRepo && bash scripts/run_sitl_rover_wsl.sh'"
}
else {
    Write-Host "  From WSL, cd to the repository root and run: bash scripts/bootstrap_wsl_ardupilot.sh"
    Write-Host "  From WSL, cd to the repository root and run: bash scripts/run_sitl_rover_wsl.sh"
}
