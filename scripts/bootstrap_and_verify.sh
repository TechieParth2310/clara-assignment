#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="$REPO_ROOT/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

# ── venv ────────────────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    python3 -m venv "$VENV_DIR" || fail "venv creation failed"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pass "venv ok"

# ── deps ────────────────────────────────────────────────────────────────────
"$PIP" install --upgrade pip -q
"$PIP" install -r requirements.txt -q || fail "pip install failed"
pass "deps ok"

# ── cli help ─────────────────────────────────────────────────────────────────
"$PYTHON" -m src.main --help > /dev/null 2>&1 || fail "python -m src.main --help failed"
pass "cli help ok"

# ── batch run ────────────────────────────────────────────────────────────────
"$PYTHON" -m src.main --input data --output outputs --mode rules --batch > /dev/null 2>&1 \
    || fail "batch run failed"
pass "batch run ok"

# ── output verification ───────────────────────────────────────────────────────
[ -f "outputs/summary/report.json" ] || fail "outputs/summary/report.json not found"
pass "report.json exists"

# Verify v1 outputs
[ -f "outputs/accounts/acme_001/v1/memo.json" ]        || fail "v1/memo.json not found"
[ -f "outputs/accounts/acme_001/v1/agent_spec.json" ]   || fail "v1/agent_spec.json not found"
[ -f "outputs/accounts/acme_001/v1/evidence.json" ]     || fail "v1/evidence.json not found"
[ -f "outputs/accounts/acme_001/v1/system_prompt.txt" ] || fail "v1/system_prompt.txt not found"
pass "v1 outputs ok"

# Verify v2 outputs
[ -f "outputs/accounts/acme_001/v2/memo.json" ]        || fail "v2/memo.json not found"
[ -f "outputs/accounts/acme_001/v2/agent_spec.json" ]   || fail "v2/agent_spec.json not found"
[ -f "outputs/accounts/acme_001/v2/evidence.json" ]     || fail "v2/evidence.json not found"
[ -f "outputs/accounts/acme_001/v2/system_prompt.txt" ] || fail "v2/system_prompt.txt not found"
pass "v2 outputs ok"

# Verify changelog
[ -f "outputs/accounts/acme_001/changes.md" ] || fail "changes.md not found"
pass "changelog ok"

# Verify diff viewer
[ -f "outputs/diff_viewer.html" ] || fail "outputs/diff_viewer.html not found"
pass "diff_viewer.html ok"

# Verify validate-only mode
"$PYTHON" -m src.main --validate-only > /dev/null 2>&1 || fail "validate-only mode failed"
pass "validate-only ok"

# Verify idempotency (re-run should produce identical output)
OLD_HASH=$(shasum outputs/accounts/acme_001/v2/memo.json | awk '{print $1}')
"$PYTHON" -m src.main --input data --output outputs --mode rules --batch > /dev/null 2>&1
NEW_HASH=$(shasum outputs/accounts/acme_001/v2/memo.json | awk '{print $1}')
[ "$OLD_HASH" = "$NEW_HASH" ] || fail "idempotency failed — memo changed on re-run"
pass "idempotency ok"

echo ""
echo "All checks passed ✅"
