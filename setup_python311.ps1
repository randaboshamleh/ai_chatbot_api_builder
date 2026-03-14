# Script to setup Python 3.11 and enable full RAG
# Run: .\setup_python311.ps1

Write-Host "=== Setting up Python 3.11 for Full RAG ===" -ForegroundColor Green
Write-Host ""

# Check for Python 3.11
Write-Host "1. Checking for Python 3.11..." -ForegroundColor Yellow
try {
    $version = py -3.11 --version 2>&1
    if ($version -match "3.11") {
        Write-Host "OK Python 3.11 found: $version" -ForegroundColor Green
    }
    else {
        Write-Host "ERROR Python 3.11 not found" -ForegroundColor Red
        Write-Host "Please download from: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "Choose Python 3.11.9" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Host "ERROR Python not found" -ForegroundColor Red
    Write-Host "Please download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Create virtual environment
Write-Host "2. Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv311") {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
    $response = Read-Host "Delete and recreate? (y/n)"
    if ($response -eq "y") {
        Remove-Item -Recurse -Force venv311
        py -3.11 -m venv venv311
        Write-Host "OK New virtual environment created" -ForegroundColor Green
    }
}
else {
    py -3.11 -m venv venv311
    Write-Host "OK Virtual environment created" -ForegroundColor Green
}

Write-Host ""

# Activate virtual environment
Write-Host "3. Activating virtual environment..." -ForegroundColor Yellow
& .\venv311\Scripts\Activate.ps1

# Check version
$currentVersion = python --version
Write-Host "OK Current version: $currentVersion" -ForegroundColor Green

Write-Host ""

# Upgrade pip
Write-Host "4. Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "OK pip upgraded" -ForegroundColor Green

Write-Host ""

# Install basic packages
Write-Host "5. Installing basic packages..." -ForegroundColor Yellow
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers --quiet
pip install celery redis langchain-text-splitters pypdf python-docx ollama --quiet
pip install psycopg2-binary python-decouple --quiet
Write-Host "OK Basic packages installed" -ForegroundColor Green

Write-Host ""

# Install ChromaDB
Write-Host "6. Installing ChromaDB..." -ForegroundColor Yellow
pip install chromadb==0.4.22 --quiet
Write-Host "OK ChromaDB installed" -ForegroundColor Green

Write-Host ""

# Test ChromaDB
Write-Host "7. Testing ChromaDB..." -ForegroundColor Yellow
$chromaTest = python -c "import chromadb; print('OK')" 2>&1
if ($chromaTest -match "OK") {
    Write-Host "OK ChromaDB working correctly" -ForegroundColor Green
}
else {
    Write-Host "ERROR Problem with ChromaDB" -ForegroundColor Red
    Write-Host $chromaTest
}

Write-Host ""

# Enable ChromaDB in code
Write-Host "8. Enabling ChromaDB in code..." -ForegroundColor Yellow
$vectorStorePath = "core\rag\vector_store.py"
$content = Get-Content $vectorStorePath -Raw -Encoding UTF8

if ($content -match "# ChromaDB") {
    $newContent = $content -replace "# ChromaDB[^\n]*\n# try:\n#     import chromadb\n#     CHROMADB_AVAILABLE = True\n# except ImportError:\nCHROMADB_AVAILABLE = False\nchromadb = None", "try:`n    import chromadb`n    CHROMADB_AVAILABLE = True`nexcept ImportError:`n    CHROMADB_AVAILABLE = False`n    chromadb = None"
    Set-Content $vectorStorePath $newContent -Encoding UTF8
    Write-Host "OK ChromaDB enabled in vector_store.py" -ForegroundColor Green
}
else {
    Write-Host "ChromaDB already enabled" -ForegroundColor Yellow
}

Write-Host ""

# Run migrations
Write-Host "9. Running migrations..." -ForegroundColor Yellow
python manage.py migrate --no-input
Write-Host "OK Migrations completed" -ForegroundColor Green

Write-Host ""

# Check Django
Write-Host "10. Checking Django..." -ForegroundColor Yellow
$djangoCheck = python manage.py check 2>&1
if ($djangoCheck -match "no issues") {
    Write-Host "OK Django working without issues" -ForegroundColor Green
}
else {
    Write-Host "WARNING Some issues may exist" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup completed successfully! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run ChromaDB (optional):" -ForegroundColor White
Write-Host "   docker run -p 8000:8000 chromadb/chroma" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run Ollama (optional):" -ForegroundColor White
Write-Host "   ollama serve" -ForegroundColor Gray
Write-Host "   ollama pull llama3" -ForegroundColor Gray
Write-Host "   ollama pull nomic-embed-text" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Run server:" -ForegroundColor White
Write-Host "   python manage.py runserver" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Access admin panel:" -ForegroundColor White
Write-Host "   http://localhost:8000/admin/" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: Virtual environment is now active (venv311)" -ForegroundColor Yellow
Write-Host "To activate in future: .\venv311\Scripts\Activate.ps1" -ForegroundColor Yellow
