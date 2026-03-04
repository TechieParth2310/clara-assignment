#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODEL="${1:-llama3.2:3b}"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

fail() { echo "❌ $1"; exit 1; }

# ── venv ────────────────────────────────────────────────────────────────────
[ -f "$REPO_ROOT/.venv/bin/activate" ] || fail ".venv not found — run: bash scripts/bootstrap_and_verify.sh"
# shellcheck disable=SC1091
source "$REPO_ROOT/.venv/bin/activate"

# ── Ollama reachability ──────────────────────────────────────────────────────
curl -sf http://127.0.0.1:11434/api/tags > /dev/null 2>&1 \
    || fail "Ollama is not reachable at http://127.0.0.1:11434 — run: ollama serve"
echo "✅ Ollama reachable"

# ── batch run ────────────────────────────────────────────────────────────────
echo "Running pipeline (mode=ollama, model=$MODEL)..."
"$VENV_PYTHON" -m src.main --input data --output outputs --mode ollama --model "$MODEL" --batch

echo ""
echo "✅ Done. Report: $REPO_ROOT/outputs/summary/report.json"
