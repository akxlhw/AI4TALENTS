# local_test.ps1
# One-click test runner for Windows — starts PostgreSQL if needed, then runs pytest.
# Usage:  .\scripts\local_test.ps1
# Requires: PowerShell 5.1+, uv, Docker Desktop (optional, for auto-starting PostgreSQL)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

function Write-Step($msg) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Fail($msg) {
    Write-Host "`n[FAIL] $msg" -ForegroundColor Red
    exit 1
}

function Write-Pass($msg) {
    Write-Host "`n[PASS] $msg" -ForegroundColor Green
}

$PG_PORT = 5432
$PG_USER = "postgres"
$PG_PASS = "postgres"
$PG_DB = "talent_db_test"
$DOCKER_CONTAINER = "talent-ci-postgres"

# --- Check if PostgreSQL is already running ---
Write-Step "Checking PostgreSQL on port $PG_PORT"
$pgReady = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $PG_PORT)
    if ($conn.Connected) {
        $conn.Close()
        $pgReady = $true
        Write-Host "PostgreSQL already running on port $PG_PORT" -ForegroundColor Green
    }
} catch {
    Write-Host "No PostgreSQL found on port $PG_PORT" -ForegroundColor Yellow
}

$startedContainer = $false
if (-not $pgReady) {
    Write-Step "Starting PostgreSQL via Docker"
    try {
        $docker = & docker --version
        Write-Host "Docker: $docker"
    } catch {
        Write-Fail "Docker not found. Either:`n  1. Start PostgreSQL manually on port $PG_PORT, or`n  2. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    }

    # Remove existing container if present
    & docker rm -f $DOCKER_CONTAINER 2>$null | Out-Null

    & docker run -d `
        --name $DOCKER_CONTAINER `
        -e POSTGRES_USER=$PG_USER `
        -e POSTGRES_PASSWORD=$PG_PASS `
        -e POSTGRES_DB=$PG_DB `
        -p ${PG_PORT}:5432 `
        --health-cmd "pg_isready" `
        --health-interval 5s `
        --health-timeout 3s `
        --health-retries 5 `
        postgres:15

    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to start PostgreSQL container" }

    Write-Host "Waiting for PostgreSQL to be healthy..." -NoNewline
    $maxWait = 30
    $elapsed = 0
    while ($elapsed -lt $maxWait) {
        $health = & docker inspect --format='{{.State.Health.Status}}' $DOCKER_CONTAINER 2>$null
        if ($health -eq "healthy") { break }
        Start-Sleep -Seconds 1
        $elapsed++
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if ($health -ne "healthy") {
        & docker logs $DOCKER_CONTAINER
        Write-Fail "PostgreSQL container did not become healthy within ${maxWait}s"
    }

    $startedContainer = $true
    Write-Pass "PostgreSQL container is healthy"
}

# --- Run tests ---
Write-Step "Running backend tests"
Set-Location "$root\backend"
$env:DATABASE_URL = "postgresql+asyncpg://${PG_USER}:${PG_PASS}@localhost:${PG_PORT}/${PG_DB}"

& uv run pytest tests/ -v --tb=short
$testExit = $LASTEXITCODE

# --- Cleanup ---
if ($startedContainer) {
    Write-Step "Stopping temporary PostgreSQL container"
    & docker stop $DOCKER_CONTAINER | Out-Null
    & docker rm $DOCKER_CONTAINER | Out-Null
    Write-Pass "Container removed"
}

if ($testExit -ne 0) {
    Write-Fail "Tests failed"
}

Write-Pass "All tests passed"
Set-Location $root
