#!/usr/bin/env bash
# Secret scanning with git-secrets, detect-secrets, and truffleHog

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPORT_DIR="${REPO_ROOT}/.build/reports"
mkdir -p "${REPORT_DIR}"

echo "=== Secret Scanning Report ===" > "${REPORT_DIR}/secret-scan.txt"

# 1. git-secrets
echo "[1/4] Running git-secrets..."
if command -v git-secrets &> /dev/null; then
  git-secrets --scan-repo "${REPO_ROOT}" >> "${REPORT_DIR}/secret-scan.txt" 2>&1 || true
else
  echo "git-secrets not installed, skipping" >> "${REPORT_DIR}/secret-scan.txt"
fi

# 2. detect-secrets
echo "[2/4] Running detect-secrets..."
if command -v detect-secrets &> /dev/null; then
  detect-secrets scan "${REPO_ROOT}" > "${REPORT_DIR}/detect-secrets.json" 2>&1 || true
  detect-secrets audit "${REPORT_DIR}/detect-secrets.json" >> "${REPORT_DIR}/secret-scan.txt" 2>&1 || true
else
  echo "detect-secrets not installed, skipping" >> "${REPORT_DIR}/secret-scan.txt"
fi

# 3. truffleHog
echo "[3/4] Running truffleHog..."
if command -v trufflehog &> /dev/null; then
  trufflehog filesystem "${REPO_ROOT}" --json > "${REPORT_DIR}/trufflehog.json" 2>&1 || true
else
  echo "truffleHog not installed, skipping" >> "${REPORT_DIR}/secret-scan.txt"
fi

# 4. Custom patterns
echo "[4/4] Running custom pattern scan..."
grep -rE \
  '(password|secret|token|api[_-]?key)\s*=\s*["\047][^"\047]{8,}' \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" \
  "${REPO_ROOT}/src" "${REPO_ROOT}/packages" "${REPO_ROOT}/apps" \
  >> "${REPORT_DIR}/secret-scan.txt" 2>&1 || true

echo "Secret scan complete. Report: ${REPORT_DIR}/secret-scan.txt"
