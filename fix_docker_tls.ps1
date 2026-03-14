# ============================================
# Fix Docker TLS Issues
# ============================================

Write-Host "=== Fixing Docker TLS/DNS Issues ===" -ForegroundColor Cyan

# 1. Restart Docker Desktop
Write-Host "`n1. Restarting Docker Desktop..." -ForegroundColor Yellow
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "Waiting 30 seconds for Docker to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# 2. Test Docker
Write-Host "`n2. Testing Docker..." -ForegroundColor Yellow
docker version

# 3. Clear Docker cache
Write-Host "`n3. Clearing Docker build cache..." -ForegroundColor Yellow
docker builder prune -f

# 4. Test connection to Docker Hub
Write-Host "`n4. Testing connection to Docker Hub..." -ForegroundColor Yellow
Test-NetConnection registry-1.docker.io -Port 443

# 5. Try to pull a small image
Write-Host "`n5. Testing pull with a small image..." -ForegroundColor Yellow
docker pull hello-world

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "If hello-world pulled successfully, try: docker-compose up -d" -ForegroundColor Cyan
Write-Host "If still failing, run project locally: .\run_local.ps1" -ForegroundColor Yellow
