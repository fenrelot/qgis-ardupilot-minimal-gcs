<#
Create a clean deployment zip for copying this project to a field laptop.

Working directory: repository root.

Examples:
  .\scripts\new_deployment_bundle.ps1
  .\scripts\new_deployment_bundle.ps1 -OutputPath C:\Temp\qgisarduboat_blueboat.zip
#>

[CmdletBinding()]
param(
    [string]$OutputPath = "",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$TmpRoot = Join-Path $RepoRoot "tmp"
$UsingDefaultOutputPath = [string]::IsNullOrWhiteSpace($OutputPath)
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $TmpRoot "qgisarduboat_blueboat_deployment.zip"
}
$ResolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)

$ExcludedDirectoryNames = @(
    ".git",
    ".venv",
    ".ruff_cache",
    ".pytest_cache",
    "logs",
    "tmp",
    "pytest-temp"
)

function Test-IsExcludedPath {
    param([System.IO.FileSystemInfo]$Item)

    $relative = [System.IO.Path]::GetRelativePath($RepoRoot, $Item.FullName)
    $parts = $relative -split "[\\/]"
    foreach ($part in $parts) {
        if ($ExcludedDirectoryNames -contains $part) {
            return $true
        }
        if ($part -like "pytest-cache-files-*") {
            return $true
        }
        if ($part -eq "__pycache__") {
            return $true
        }
    }
    if ($Item -is [System.IO.FileInfo]) {
        if ($Item.Extension -in @(".pyc", ".pyo")) {
            return $true
        }
        if ($Item.Name -like "*.qgz~") {
            return $true
        }
    }
    return $false
}

function Get-IncludedFiles {
    param([string]$Root)

    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($Root)
    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $current -Force) {
            if (Test-IsExcludedPath $item) {
                continue
            }
            if ($item -is [System.IO.DirectoryInfo]) {
                $stack.Push($item.FullName)
                continue
            }
            if ($item -is [System.IO.FileInfo]) {
                $item
            }
        }
    }
}

Write-Host "Working directory: $RepoRoot"
Write-Host "Output zip: $ResolvedOutputPath"

$files = @(Get-IncludedFiles -Root $RepoRoot)

if ($CheckOnly) {
    Write-Host "CheckOnly: would package $($files.Count) files."
    return
}

New-Item -ItemType Directory -Force -Path $TmpRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ResolvedOutputPath) | Out-Null
if (Test-Path -LiteralPath $ResolvedOutputPath) {
    try {
        Remove-Item -LiteralPath $ResolvedOutputPath -Force
    }
    catch {
        if (-not $UsingDefaultOutputPath) {
            throw
        }
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $ResolvedOutputPath = Join-Path $TmpRoot "qgisarduboat_blueboat_deployment_$timestamp.zip"
        Write-Warning "Could not overwrite the existing zip. Writing a timestamped bundle instead: $ResolvedOutputPath"
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($ResolvedOutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in $files) {
        $relative = [System.IO.Path]::GetRelativePath($RepoRoot, $file.FullName) -replace "\\", "/"
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $file.FullName,
            $relative,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Deployment bundle created:"
Write-Host "  $ResolvedOutputPath"
