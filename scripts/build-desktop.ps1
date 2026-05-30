# CityOS Jarvis Desktop Build Script (Windows)
# Usage: .\scripts\build-desktop.ps1 [platform]
# Platforms: windows, all

param(
    [string]$Platform = "windows"
)

$APP_DIR = "apps/cityos-jarvis-desktop"

Write-Host "=== CityOS Jarvis Desktop Build ===" -ForegroundColor Cyan
Write-Host "Platform: $Platform"

# Verify prerequisites
if (!(Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Error "pnpm not found"
    exit 1
}

if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Rust/Cargo not found"
    exit 1
}

# Build frontend
Write-Host "Building frontend..." -ForegroundColor Green
Set-Location $APP_DIR
pnpm install
pnpm build

# Build Tauri
Write-Host "Building Tauri app..." -ForegroundColor Green
switch ($Platform) {
    "windows" {
        pnpm tauri build --target x86_64-pc-windows-msvc
    }
    "all" {
        pnpm tauri build
    }
    default {
        Write-Error "Unknown platform: $Platform"
        exit 1
    }
}

Write-Host "=== Build Complete ===" -ForegroundColor Green
Write-Host "Artifacts in: $APP_DIR/src-tauri/target/release/bundle/"
