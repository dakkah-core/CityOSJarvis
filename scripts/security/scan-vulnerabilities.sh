#!/usr/bin/env bash
# Vulnerability scanning with trivy, safety, and npm audit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPORT_DIR="${REPO_ROOT}/.build/reports"
mkdir -p "${REPORT_DIR}"

echo "=== Vulnerability Scanning Report ===" > "${REPORT_DIR}/vuln-scan.txt"

# 1. Trivy filesystem scan
echo "[1/4] Running Trivy filesystem scan..."
if command -v trivy &> /dev/null; then
  trivy fs --scanners vuln,secret,config \
    --format json \
    --output "${REPORT_DIR}/trivy-fs.json" \
    "${REPO_ROOT}" 2>&1 || true
  trivy fs --scanners vuln \
    --format table \
    --output "${REPORT_DIR}/vuln-scan.txt" \
    "${REPO_ROOT}" 2>&1 || true
else
  echo "Trivy not installed, skipping" >> "${REPORT_DIR}/vuln-scan.txt"
fi

# 2. Python safety check
echo "[2/4] Running safety check..."
cd "${REPO_ROOT}"
if command -v safety &> /dev/null; then
  safety check --json > "${REPORT_DIR}/safety.json" 2>&1 || true
else
  echo "safety not installed, skipping" >> "${REPORT_DIR}/vuln-scan.txt"
fi

# 3. pip-audit
echo "[3/4] Running pip-audit..."
if command -v pip-audit &> /dev/null; then
  pip-audit --format=json --output="${REPORT_DIR}/pip-audit.json" 2>&1 || true
else
  echo "pip-audit not installed, skipping" >> "${REPORT_DIR}/vuln-scan.txt"
fi

# 4. Docker image scan (if image exists)
echo "[4/4] Running Trivy image scan..."
if command -v trivy &> /dev/null && docker images cityosjarvis:latest --format "{{.Repository}}" | grep -q cityosjarvis; then
  trivy image --scanners vuln \
    --format json \
    --output "${REPORT_DIR}/trivy-image.json" \
    cityosjarvis:latest 2>&1 || true
else
  echo "Trivy image scan skipped (image not built)" >> "${REPORT_DIR}/vuln-scan.txt"
fi

echo "Vulnerability scan complete. Report: ${REPORT_DIR}/vuln-scan.txt"
