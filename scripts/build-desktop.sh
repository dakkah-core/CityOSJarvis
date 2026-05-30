#!/usr/bin/env bash
set -euo pipefail

# CityOSJarvis Desktop Build Script
# Cross-platform Tauri v2 builds

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/apps/cityos-jarvis-desktop"

echo "=== CityOSJarvis Desktop Build ==="
echo "Root: $ROOT_DIR"
echo "Desktop: $DESKTOP_DIR"

# Detect platform
OS=$(uname -s)
ARCH=$(uname -m)
echo "Platform: $OS / $ARCH"

# Check prerequisites
check_cmd() {
  if ! command -v "$1" &> /dev/null; then
    echo "ERROR: $1 is not installed"
    exit 1
  fi
}

check_cmd node
check_cmd pnpm
check_cmd cargo

cd "$DESKTOP_DIR"

# Install dependencies
echo "=== Installing dependencies ==="
pnpm install

# Build frontend
echo "=== Building frontend ==="
pnpm build

# Build Tauri
echo "=== Building Tauri app ==="
if [ "$OS" = "Darwin" ]; then
  # macOS
  if [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    echo "Signing with identity: $APPLE_SIGNING_IDENTITY"
    export TAURI_SIGNING_IDENTITY="$APPLE_SIGNING_IDENTITY"
  fi
  pnpm tauri build --target universal-apple-darwin
elif [ "$OS" = "Linux" ]; then
  # Linux
  pnpm tauri build
else
  echo "ERROR: Unsupported platform: $OS"
  exit 1
fi

# Report outputs
echo ""
echo "=== Build outputs ==="
find "$DESKTOP_DIR/src-tauri/target" -type f \( \
  -name "*.dmg" -o \
  -name "*.app" -o \
  -name "*.AppImage" -o \
  -name "*.deb" -o \
  -name "*.rpm" \
) -print 2>/dev/null || true

echo ""
echo "=== Build complete ==="
