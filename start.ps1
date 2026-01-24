# GraphGuard - Start All Services
# Run with: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GraphGuard - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$projectRoot = $PSScriptRoot

# Option 1: Quick Demo (no dependencies)
Write-Host "`n[Option 1] Quick Demo - Opening standalone.html..." -ForegroundColor Yellow
$standalonePath = Join-Path $projectRoot "frontend\standalone.html"
if (Test-Path $standalonePath) {
    Start-Process $standalonePath
    Write-Host "Opened standalone demo in browser!" -ForegroundColor Green
}

# Option 2: Full Stack (requires dependencies)
Write-Host "`n[Option 2] To run full stack:" -ForegroundColor Yellow
Write-Host @"

Step 1 - Configure environment:
  Copy .env.example to .env and set secrets

Step 2 - Start Docker services:
  docker-compose up -d

Step 3 - Install Python dependencies (in new terminal):
  cd $projectRoot
  pip install fastapi uvicorn redis structlog pydantic

Step 4 - Start FastAPI backend (in new terminal):
  cd $projectRoot\ml\serving
  $env:API_KEY="change-me"
  $env:CORS_ALLOW_ORIGINS="http://localhost:3000"
  python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Step 5 - Install & start frontend (in new terminal):
  cd $projectRoot\frontend
  pnpm install
  pnpm dev

  # If pnpm is not available:
  #   corepack enable
  #   corepack prepare pnpm@10.21.0 --activate
  #   pnpm install
  #   pnpm dev

Dashboard will be at: http://localhost:3000
API will be at: http://localhost:8000

"@ -ForegroundColor White

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Standalone demo opened in browser!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
