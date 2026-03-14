# ============================================
# API Testing Script
# ============================================

param(
    [string]$ApiKey = "",
    [string]$Question = "What services are available?"
)

Write-Host "=== Testing /api/v1/chat/query/ ===" -ForegroundColor Cyan

if ([string]::IsNullOrEmpty($ApiKey)) {
    Write-Host "Warning: No API Key provided. Make sure to create a tenant and get the api_key" -ForegroundColor Yellow
    Write-Host "Usage: .\test_api.ps1 -ApiKey 'your-api-key-here'" -ForegroundColor Yellow
    Write-Host ""
}

$headers = @{
    "Content-Type" = "application/json"
}

if (-not [string]::IsNullOrEmpty($ApiKey)) {
    $headers["X-API-Key"] = $ApiKey
}

$body = @{
    question = $Question
    stream = $false
} | ConvertTo-Json

Write-Host "Request:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "http://localhost/api/v1/chat/query/" `
        -Method POST `
        -Headers $headers `
        -Body $body `
        -TimeoutSec 60

    Write-Host "Success! Response:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
} catch {
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Error details:" -ForegroundColor Yellow
        Write-Host $responseBody
    }
}

Write-Host "`n=== Checking API logs for errors ===" -ForegroundColor Cyan
docker-compose logs api --tail=20
