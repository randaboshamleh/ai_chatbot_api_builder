# ============================================
# Run Project Locally (without Docker)
# ============================================

Write-Host "=== Activating Python 3.11 environment ===" -ForegroundColor Cyan
& .\venv311\Scripts\Activate.ps1

Write-Host "`n=== Checking Python version ===" -ForegroundColor Yellow
python --version

Write-Host "`n=== Running migrations ===" -ForegroundColor Cyan
python manage.py migrate

Write-Host "`n=== Starting Django server ===" -ForegroundColor Green
Write-Host "Server will run on: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Admin panel: http://localhost:8000/admin/" -ForegroundColor Cyan
Write-Host "API endpoint: http://localhost:8000/api/v1/chat/query/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python manage.py runserver
