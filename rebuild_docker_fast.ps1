# ============================================
# Fast Docker Rebuild (keeps volumes & models)
# ============================================

Write-Host "=== Stopping containers ===" -ForegroundColor Yellow
docker-compose down

Write-Host "`n=== Rebuilding API image only ===" -ForegroundColor Cyan
docker-compose build api

Write-Host "`n=== Starting all containers ===" -ForegroundColor Green
docker-compose up -d

Write-Host "`n=== Waiting for services (20 seconds) ===" -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host "`n=== Checking container status ===" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n=== Testing ChromaDB connection ===" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] ChromaDB is working!" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] ChromaDB is not responding" -ForegroundColor Red
}

Write-Host "`n=== Running migrations ===" -ForegroundColor Cyan
docker-compose exec -T api python manage.py migrate

Write-Host "`n=== Checking API logs ===" -ForegroundColor Cyan
docker-compose logs api --tail=30

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "API endpoint: http://localhost/api/v1/chat/query/" -ForegroundColor Cyan
Write-Host "Admin panel: http://localhost/admin/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Run .\verify_docker.ps1 to check everything" -ForegroundColor Yellow
