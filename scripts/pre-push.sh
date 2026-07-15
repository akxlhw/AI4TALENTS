#!/usr/bin/env bash
# Pre-push hook — runs CI-equivalent checks before allowing a push.
#
# Install (run once from repo root):
#   cp scripts/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
#
# Skip temporarily: git push --no-verify
#
# This hook replicates the GitHub Actions backend-lint job:
#   1. ruff check (lint)
#   2. black --check (format)
#   3. mypy gate (type checking with baseline)
#   4. architecture compliance
#
# If any check fails, the push is aborted.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
BACKEND_DIR="$REPO_ROOT/backend"

echo "============================================"
echo "  Pre-push CI checks (backend-lint)"
echo "============================================"
echo ""

cd "$BACKEND_DIR"

# 1. Ruff
echo "[1/4] Ruff lint..."
if ! uv run ruff check app tests 2>&1; then
  echo ""
  echo "❌ Ruff check failed. Fix with: uv run ruff check --fix app tests"
  exit 1
fi
echo "  ✅ Ruff passed"
echo ""

# 2. Black
echo "[2/4] Black format check..."
if ! uv run black --check app tests 2>&1; then
  echo ""
  echo "❌ Black check failed. Fix with: uv run black app tests"
  exit 1
fi
echo "  ✅ Black passed"
echo ""

# 3. Mypy gate
echo "[3/4] Mypy gate..."
if ! uv run python scripts/ops/mypy_gate.py 2>&1; then
  echo ""
  echo "❌ Mypy gate failed. Either fix the new type errors, or regenerate baseline:"
  echo "   cd backend && uv run python scripts/ops/mypy_gate.py --regenerate"
  exit 1
fi
echo "  ✅ Mypy gate passed"
echo ""

# 4. Architecture compliance
echo "[4/4] Architecture compliance..."
if ! uv run python scripts/check_architecture.py 2>&1; then
  echo ""
  echo "❌ Architecture check failed. Fix cross-layer imports or update baseline:"
  echo "   cd backend && uv run python scripts/check_architecture.py --update-baseline"
  exit 1
fi
echo "  ✅ Architecture passed"
echo ""

echo "============================================"
echo "  All pre-push checks passed ✅"
echo "============================================"
