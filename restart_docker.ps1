# ============================================
# Simple Docker Restart (no rebuild needed)
# ============================================

Write-Host "=== Checking existing images ===" -ForegroundColor Cyan
docker images | Select-String -Pattern "ai-chatbot|chromadb|ollama|postgres|redis"

Write-Host "`n=== Starting containers with existing images ===" -ForegroundColor Green
docker-compose up -d

Write-Host "`n=== Waiting for services (20 seconds) ===" -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host "`n=== Checking container status ===" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n=== Testing ChromaDB ===" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] ChromaDB is working!" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] ChromaDB not responding. Checking logs..." -ForegroundColor Red
    docker-compose logs chromadb --tail=20
}

Write-Host "`n=== Checking API logs ===" -ForegroundColor Cyan
docker-compose logs api --tail=30

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "If containers are running, test with: .\test_api.ps1 -ApiKey YOUR_KEY" -ForegroundColor Cyan
