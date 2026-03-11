# Quick Start Script for Windows PowerShell
# Usage: .\quick_start.ps1
# Or: Run in PowerShell as admin

Write-Host "================================" -ForegroundColor Cyan
Write-Host "BC Pipeline - Quick Start Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "✓ Checking Python installation..." -ForegroundColor Green
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Python not found. Install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Create virtual environments if needed
Write-Host ""
Write-Host "✓ Setting up virtual environments..." -ForegroundColor Green

@("actus_engine", "blockchain_test") | ForEach-Object {
    $venv_path = ".\$_\venv"
    if (-not (Test-Path $venv_path)) {
        Write-Host "  Creating venv in $_..." -ForegroundColor Yellow
        python -m venv $venv_path
        & ".\$_\venv\Scripts\Activate.ps1"
        
        $req_file = ".\$_\requirements.txt"
        if (Test-Path $req_file) {
            Write-Host "  Installing dependencies for $_..." -ForegroundColor Yellow
            pip install -r $req_file -q
        }
        
        deactivate
        Write-Host "  ✓ $_ ready" -ForegroundColor Green
    } else {
        Write-Host "  ✓ $_ already has venv" -ForegroundColor Green
    }
}

# Install orchestrator dependencies
Write-Host ""
Write-Host "✓ Installing orchestrator dependencies..." -ForegroundColor Green
pip install requests python-dotenv web3 -q

# Check .env files
Write-Host ""
Write-Host "✓ Checking environment configurations..." -ForegroundColor Green

@("actus_engine", "blockchain_test") | ForEach-Object {
    $env_file = ".\$_\.env"
    if (Test-Path $env_file) {
        Write-Host "  ✓ $_ has .env configured" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ $_\.env MISSING - Configure before running!" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Configure .env files:" -ForegroundColor White
Write-Host "   - actus_engine/.env     (add GROQ_API_KEY)" -ForegroundColor Gray
Write-Host "   - blockchain_test/.env  (add RPC_URL, CONTRACT_ADDRESS, keys)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run the pipeline:" -ForegroundColor White
Write-Host "   python orchestrator.py --demo" -ForegroundColor Gray
Write-Host ""
Write-Host "3. For detailed help:" -ForegroundColor White
Write-Host "   python orchestrator.py --help" -ForegroundColor Gray
Write-Host ""
