#!/usr/bin/env bash
set -euo pipefail

# CityOS Jarvis Desktop Build Script
# Usage: ./scripts/build-desktop.sh [platform]
# Platforms: windows, macos, linux, all

PLATFORM="${1:-all}"
APP_DIR="apps/cityos-jarvis-desktop"

echo "=== CityOS Jarvis Desktop Build ==="
echo "Platform: $PLATFORM"

# Verify prerequisites
if ! command -v pnpm &> /dev/null; then
    echo "Error: pnpm not found"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "Error: Rust/Cargo not found"
    exit 1
fi

# Build frontend
echo "Building frontend..."
cd "$APP_DIR"
pnpm install
pnpm build

# Build Tauri
echo "Building Tauri app..."
case "$PLATFORM" in
    windows)
        pnpm tauri build --target x86_64-pc-windows-msvc
        ;;
    macos)
        pnpm tauri build --target universal-apple-darwin
        ;;
    linux)
        pnpm tauri build --target x86_64-unknown-linux-gnu
        ;;
    all)
        pnpm tauri build
        ;;
    *)
        echo "Unknown platform: $PLATFORM"
        echo "Usage: $0 [windows|macos|linux|all]"
        exit 1
        ;;
esac

echo "=== Build Complete ==="
echo "Artifacts in: $APP_DIR/src-tauri/target/release/bundle/"
