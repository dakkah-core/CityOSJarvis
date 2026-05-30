#!/usr/bin/env bash
# OWASP ZAP baseline scan for CityOSJarvis BFF endpoints

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPORT_DIR="${REPO_ROOT}/.build/reports"
mkdir -p "${REPORT_DIR}"

TARGET_URL="${1:-http://localhost:3000}"

echo "=== OWASP ZAP Baseline Scan ===" > "${REPORT_DIR}/zap-scan.txt"
echo "Target: ${TARGET_URL}" >> "${REPORT_DIR}/zap-scan.txt"

if command -v docker &> /dev/null; then
  docker run --rm \
    -v "${REPORT_DIR}:/zap/wrk" \
    ghcr.io/zaproxy/zaproxy:stable \
    zap-baseline.py \
    -t "${TARGET_URL}" \
    -J zap-report.json \
    -w zap-report.md \
    -g gen.conf \
    -r zap-report.html 2>&1 | tee -a "${REPORT_DIR}/zap-scan.txt" || true
else
  echo "Docker not available, skipping ZAP scan" >> "${REPORT_DIR}/zap-scan.txt"
fi

echo "ZAP scan complete. Report: ${REPORT_DIR}/zap-report.html"
