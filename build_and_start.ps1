# ============================================
# Build API and Start All Services
# ============================================

Write-Host "=== Building API image ===" -ForegroundColor Cyan
docker-compose build api

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Build successful!" -ForegroundColor Green
    
    Write-Host "`n=== Starting all services ===" -ForegroundColor Cyan
    docker-compose up -d
    
    Write-Host "`n=== Waiting 20 seconds ===" -ForegroundColor Yellow
    Start-Sleep -Seconds 20
    
    Write-Host "`n=== Checking status ===" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host "`n=== Running migrations ===" -ForegroundColor Cyan
    docker-compose exec -T api python manage.py migrate
    
    Write-Host "`n=== Testing ChromaDB ===" -ForegroundColor Green
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
        Write-Host "[OK] ChromaDB is working!" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] ChromaDB not responding" -ForegroundColor Red
    }
    
    Write-Host "`n=== Checking API logs ===" -ForegroundColor Cyan
    docker-compose logs api --tail=30
    
    Write-Host "`n=== Done! ===" -ForegroundColor Green
    Write-Host "API: http://localhost/api/v1/chat/query/" -ForegroundColor Cyan
    Write-Host "Admin: http://localhost/admin/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next: Run .\verify_docker.ps1 to verify everything" -ForegroundColor Yellow
} else {
    Write-Host "`n[FAIL] Build failed!" -ForegroundColor Red
    Write-Host "Try running locally instead: .\run_local.ps1" -ForegroundColor Yellow
}
