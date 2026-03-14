# ============================================
# Docker Rebuild Script
# ============================================

Write-Host "=== Stopping containers ===" -ForegroundColor Yellow
docker-compose down

Write-Host "`n=== Removing old images ===" -ForegroundColor Yellow
docker-compose down --rmi all

Write-Host "`n=== Building images ===" -ForegroundColor Cyan
docker-compose build --no-cache

Write-Host "`n=== Starting containers ===" -ForegroundColor Green
docker-compose up -d

Write-Host "`n=== Waiting for services (30 seconds) ===" -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n=== Checking container status ===" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n=== Checking API logs ===" -ForegroundColor Cyan
docker-compose logs api --tail=50

Write-Host "`n=== Testing ChromaDB connection ===" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
    Write-Host "ChromaDB is working!" -ForegroundColor Green
} catch {
    Write-Host "ChromaDB is not responding" -ForegroundColor Red
}

Write-Host "`n=== Running migrations ===" -ForegroundColor Cyan
docker-compose exec -T api python manage.py migrate

Write-Host "`n=== Collecting static files ===" -ForegroundColor Cyan
docker-compose exec -T api python manage.py collectstatic --noinput

Write-Host "`n=== Downloading Ollama models ===" -ForegroundColor Yellow
docker-compose exec ollama ollama pull llama3.2:1b
docker-compose exec ollama ollama pull nomic-embed-text

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "API endpoint: http://localhost/api/v1/chat/query/" -ForegroundColor Cyan
Write-Host "Admin panel: http://localhost/admin/" -ForegroundColor Cyan
