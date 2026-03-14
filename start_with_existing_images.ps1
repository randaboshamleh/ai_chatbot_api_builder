# ============================================
# Start Docker with existing images only
# ============================================

Write-Host "=== Stopping any running containers ===" -ForegroundColor Yellow
docker-compose down

Write-Host "`n=== Starting with existing images (no pull) ===" -ForegroundColor Green
docker-compose up -d --no-build

Write-Host "`n=== Waiting 20 seconds ===" -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host "`n=== Checking status ===" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n=== Testing ChromaDB ===" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] ChromaDB is working!" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] ChromaDB not responding" -ForegroundColor Red
    Write-Host "Checking logs..." -ForegroundColor Yellow
    docker-compose logs chromadb --tail=20
}

Write-Host "`n=== Checking API ===" -ForegroundColor Cyan
docker-compose logs api --tail=30

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "If running, access: http://localhost/admin/" -ForegroundColor Cyan
