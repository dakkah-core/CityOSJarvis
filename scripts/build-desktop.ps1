# CityOSJarvis Desktop Build Script (Windows)
# Tauri v2 MSI build

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path "$PSScriptRoot\.."
$DesktopDir = Join-Path $RootDir "apps\cityos-jarvis-desktop"

Write-Host "=== CityOSJarvis Desktop Build ===" -ForegroundColor Cyan
Write-Host "Root: $RootDir"
Write-Host "Desktop: $DesktopDir"

# Check prerequisites
function Test-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "ERROR: $Name is not installed"
  }
}

Test-Command "node"
Test-Command "pnpm"
Test-Command "cargo"

Push-Location $DesktopDir

try {
  Write-Host "=== Installing dependencies ===" -ForegroundColor Green
  pnpm install

  Write-Host "=== Building frontend ===" -ForegroundColor Green
  pnpm build

  Write-Host "=== Building Tauri MSI ===" -ForegroundColor Green
  pnpm tauri build

  # Report outputs
  Write-Host ""
  Write-Host "=== Build outputs ===" -ForegroundColor Cyan
  $OutputDir = Join-Path $DesktopDir "src-tauri\target\release\bundle"
  if (Test-Path $OutputDir) {
    Get-ChildItem -Path $OutputDir -Recurse -Include *.msi, *.exe | ForEach-Object {
      Write-Host "  $($_.FullName)" -ForegroundColor Yellow
    }
  }
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
