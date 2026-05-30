#!/usr/bin/env bash
set -euo pipefail

# Build all CityOSJarvis client applications
# Usage: ./scripts/build-all-clients.sh [web|desktop|mobile|all]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET="${1:-all}"

echo "=== CityOSJarvis Client Build ==="
echo "Target: $TARGET"
echo "Root: $ROOT_DIR"
echo ""

build_web() {
  echo "=== Building Web Platform ==="
  cd "$ROOT_DIR/apps/web-platform"
  pnpm install
  pnpm build
  echo "Web platform build complete"
  echo ""
}

build_desktop() {
  echo "=== Building Desktop App ==="
  "$SCRIPT_DIR/build-desktop.sh"
  echo "Desktop build complete"
  echo ""
}

build_mobile() {
  echo "=== Building Mobile Apps ==="
  for app in mobile mobile-inspector mobile-driver; do
    if [ -d "$ROOT_DIR/apps/$app" ]; then
      echo "Building $app..."
      cd "$ROOT_DIR/apps/$app"
      pnpm install
      # EAS build requires credentials; skip in local dev
      # pnpm eas:build --platform android
    else
      echo "Skipping $app (not found)"
    fi
  done
  echo "Mobile builds configured (run EAS builds separately with credentials)"
  echo ""
}

case "$TARGET" in
  web)
    build_web
    ;;
  desktop)
    build_desktop
    ;;
  mobile)
    build_mobile
    ;;
  all)
    build_web
    build_desktop
    build_mobile
    ;;
  *)
    echo "Usage: $0 [web|desktop|mobile|all]"
    exit 1
    ;;
esac

echo "=== All requested builds complete ==="
