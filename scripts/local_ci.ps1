# local_ci.ps1
# One-click local CI for Windows — runs the same checks as GitHub Actions.
#
# Usage:
#   .\scripts\local_ci.ps1         # CI-aligned checks (mypy + architecture + frontend)
#   .\scripts\local_ci.ps1 -Full   # Also include ruff + black
#
# Requires: PowerShell 5.1+, uv (backend), Node.js/npm (frontend)

param(
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$failedSteps = @()

function Write-Step($msg) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Fail($msg) {
    Write-Host "`n[FAIL] $msg" -ForegroundColor Red
    $script:failedSteps += $msg
}

function Write-Pass($msg) {
    Write-Host "`n[PASS] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "`n[WARN] $msg" -ForegroundColor Yellow
}

# --- Pre-flight checks ---
Write-Step "Pre-flight checks"

try { $uv = & uv --version } catch { Write-Error "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/" }
Write-Host "uv: $uv"

try { $node = & node --version } catch { Write-Error "Node.js not found. Install: https://nodejs.org/" }
Write-Host "node: $node"

try { $npm = & npm --version } catch { Write-Error "npm not found" }
Write-Host "npm: $npm"

# --- Optional: ruff + black ---
if ($Full) {
    Write-Step "Backend: Ruff check (FULL mode)"
    Set-Location "$root\backend"
    & uv run ruff check app tests
    if ($LASTEXITCODE -ne 0) { Write-Fail "Ruff check failed" } else { Write-Pass "Ruff check passed" }

    Write-Step "Backend: Black check (FULL mode)"
    & uv run black --check app tests
    if ($LASTEXITCODE -ne 0) { Write-Fail "Black check failed. Run: uv run black app tests" } else { Write-Pass "Black check passed" }
}

# --- Backend: mypy gate ---
Write-Step "Backend: Mypy gate"
Set-Location "$root\backend"
& uv run python scripts/ops/mypy_gate.py
if ($LASTEXITCODE -ne 0) { Write-Fail "Mypy gate failed" } else { Write-Pass "Mypy gate passed" }

# --- Backend: architecture compliance ---
Write-Step "Backend: Architecture compliance check"
& uv run python scripts/check_architecture.py
if ($LASTEXITCODE -ne 0) { Write-Fail "Architecture check failed" } else { Write-Pass "Architecture check passed" }

# --- Frontend lint ---
Write-Step "Frontend: ESLint"
Set-Location "$root\frontend"
& npm run lint
if ($LASTEXITCODE -ne 0) { Write-Fail "ESLint failed" } else { Write-Pass "ESLint passed" }

Write-Step "Frontend: npm audit"
& npm audit --registry https://registry.npmjs.org
if ($LASTEXITCODE -ne 0) {
    Write-Warn "npm audit found vulnerabilities (non-blocking locally)"
} else {
    Write-Pass "npm audit passed"
}

Write-Step "Frontend: Build"
& npm run build
if ($LASTEXITCODE -ne 0) { Write-Fail "Frontend build failed" } else { Write-Pass "Frontend build passed" }

# --- Summary ---
Write-Step "LOCAL CI SUMMARY"
if ($failedSteps.Count -eq 0) {
    Write-Host "All CI-aligned checks passed! This commit should pass remote CI." -ForegroundColor Green
    if (-not $Full) {
        Write-Host "Run with -Full to also check ruff + black." -ForegroundColor DarkGray
    }
    Set-Location $root
    exit 0
} else {
    Write-Host "The following checks failed:" -ForegroundColor Red
    foreach ($step in $failedSteps) {
        Write-Host "  - $step" -ForegroundColor Red
    }
    Set-Location $root
    exit 1
}
