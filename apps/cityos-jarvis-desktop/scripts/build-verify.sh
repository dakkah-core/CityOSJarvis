#!/usr/bin/env bash
# Desktop build verification for Tauri v2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/.build/reports"
mkdir -p "${REPORT_DIR}"

echo "=== CityOSJarvis Desktop Build Verification ==="

# Prerequisites check
echo "[1/5] Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "ERROR: Rust/Cargo not found"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo "WARNING: pnpm not found, trying npm"
    NPM_CMD="npm"
else
    NPM_CMD="pnpm"
fi

NODE_VERSION=$(node --version)
echo "Node.js: ${NODE_VERSION}"
RUST_VERSION=$(rustc --version)
echo "Rust: ${RUST_VERSION}"

# Install dependencies
echo "[2/5] Installing dependencies..."
cd "${PROJECT_ROOT}"
${NPM_CMD} install

# Type check
echo "[3/5] Type checking..."
npx tsc --noEmit > "${REPORT_DIR}/desktop-tsc.log" 2>&1 || {
    echo "Type check failed. See ${REPORT_DIR}/desktop-tsc.log"
    exit 1
}

# Build web assets
echo "[4/5] Building web assets..."
${NPM_CMD} run build > "${REPORT_DIR}/desktop-build.log" 2>&1 || {
    echo "Web build failed. See ${REPORT_DIR}/desktop-build.log"
    exit 1
}

# Tauri build
echo "[5/5] Building Tauri app..."
cd "${PROJECT_ROOT}/src-tauri"
cargo build --release > "${REPORT_DIR}/desktop-tauri-build.log" 2>&1 || {
    echo "Tauri build failed. See ${REPORT_DIR}/desktop-tauri-build.log"
    exit 1
}

# Verify binary exists
BINARY_PATH=""
case "$(uname -s)" in
    Linux*)     BINARY_PATH="${PROJECT_ROOT}/src-tauri/target/release/cityos-jarvis-desktop" ;;
    Darwin*)    BINARY_PATH="${PROJECT_ROOT}/src-tauri/target/release/cityos-jarvis-desktop" ;;
    CYGWIN*|MINGW*|MSYS*) BINARY_PATH="${PROJECT_ROOT}/src-tauri/target/release/cityos-jarvis-desktop.exe" ;;
esac

if [ -f "${BINARY_PATH}" ]; then
    echo "Build successful: ${BINARY_PATH}"
    ls -lh "${BINARY_PATH}"
else
    echo "ERROR: Binary not found at ${BINARY_PATH}"
    exit 1
fi

# Bundle check (optional)
BUNDLE_DIR="${PROJECT_ROOT}/src-tauri/target/release/bundle"
if [ -d "${BUNDLE_DIR}" ]; then
    echo "Bundles created:"
    find "${BUNDLE_DIR}" -type f -ls || true
fi

echo "=== Desktop Build Verification Complete ==="
