# ============================================
# Docker Setup Verification Script
# ============================================

Write-Host "=== Docker Setup Verification ===" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# 1. Check containers
Write-Host "1. Checking container status..." -ForegroundColor Yellow
$containers = docker-compose ps --format json | ConvertFrom-Json
$requiredServices = @('api', 'chromadb', 'ollama', 'postgres', 'redis', 'nginx')

foreach ($service in $requiredServices) {
    $container = $containers | Where-Object { $_.Service -eq $service }
    if ($container -and $container.State -eq 'running') {
        Write-Host "   [OK] $service is running" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] $service is not running" -ForegroundColor Red
        $allGood = $false
    }
}
Write-Host ""

# 2. Check ChromaDB
Write-Host "2. Checking ChromaDB connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/heartbeat" -Method GET -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "   [OK] ChromaDB is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "   [FAIL] ChromaDB is not responding" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# 3. Check Ollama models
Write-Host "3. Checking Ollama models..." -ForegroundColor Yellow
try {
    $ollamaModels = docker-compose exec -T ollama ollama list 2>&1
    if ($ollamaModels -match "llama3" -or $ollamaModels -match "llama") {
        Write-Host "   [OK] LLM model found" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] LLM model not found" -ForegroundColor Yellow
        Write-Host "   Run: docker-compose exec ollama ollama pull llama3.2:1b" -ForegroundColor Cyan
    }
    
    if ($ollamaModels -match "nomic-embed-text") {
        Write-Host "   [OK] Embedding model found" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] Embedding model not found" -ForegroundColor Yellow
        Write-Host "   Run: docker-compose exec ollama ollama pull nomic-embed-text" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   [FAIL] Failed to check Ollama" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# 4. Check Django migrations
Write-Host "4. Checking Django migrations..." -ForegroundColor Yellow
try {
    $migrations = docker-compose exec -T api python manage.py showmigrations --plan 2>&1
    if ($migrations -match "\[X\]") {
        Write-Host "   [OK] Migrations applied" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] Migrations may need to be applied" -ForegroundColor Yellow
        Write-Host "   Run: docker-compose exec api python manage.py migrate" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   [FAIL] Failed to check migrations" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# 5. Check .env file
Write-Host "5. Checking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    $requiredVars = @('CHROMA_HOST', 'CHROMA_PORT', 'OLLAMA_BASE_URL', 'DB_HOST', 'REDIS_URL')
    
    foreach ($var in $requiredVars) {
        if ($envContent -match $var) {
            Write-Host "   [OK] $var exists" -ForegroundColor Green
        } else {
            Write-Host "   [FAIL] $var missing" -ForegroundColor Red
            $allGood = $false
        }
    }
} else {
    Write-Host "   [FAIL] .env file not found" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# 6. Check API logs for errors
Write-Host "6. Checking API logs for errors..." -ForegroundColor Yellow
$apiLogs = docker-compose logs api --tail=50 2>&1
if ($apiLogs -match "ERROR" -or $apiLogs -match "CRITICAL") {
    Write-Host "   [WARN] Errors found in logs" -ForegroundColor Yellow
    Write-Host "   Review logs: docker-compose logs api" -ForegroundColor Cyan
} else {
    Write-Host "   [OK] No obvious errors" -ForegroundColor Green
}
Write-Host ""

# 7. Check ports
Write-Host "7. Checking required ports..." -ForegroundColor Yellow
$ports = @{
    '80' = 'Nginx'
    '8001' = 'ChromaDB'
    '5050' = 'pgAdmin'
    '9001' = 'MinIO'
}

foreach ($port in $ports.Keys) {
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($connection) {
            Write-Host "   [OK] Port $port ($($ports[$port])) is open" -ForegroundColor Green
        } else {
            Write-Host "   [FAIL] Port $port ($($ports[$port])) is closed" -ForegroundColor Red
        }
    } catch {
        Write-Host "   [WARN] Failed to check port $port" -ForegroundColor Yellow
    }
}
Write-Host ""

# Final result
Write-Host "=== Final Result ===" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "[SUCCESS] All checks passed! System is ready" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Create superuser: docker-compose exec api python manage.py createsuperuser" -ForegroundColor White
    Write-Host "2. Access admin panel: http://localhost/admin/" -ForegroundColor White
    Write-Host "3. Create tenant and get API Key" -ForegroundColor White
    Write-Host "4. Upload document: POST http://localhost/api/v1/documents/upload/" -ForegroundColor White
    Write-Host "5. Test query: .\test_api.ps1 -ApiKey 'YOUR_KEY'" -ForegroundColor White
} else {
    Write-Host "[FAIL] Some checks failed. Review errors above" -ForegroundColor Red
    Write-Host ""
    Write-Host "For help, check:" -ForegroundColor Yellow
    Write-Host "- DOCKER_TROUBLESHOOTING.md" -ForegroundColor White
    Write-Host "- docker-compose logs api" -ForegroundColor White
}
Write-Host ""
