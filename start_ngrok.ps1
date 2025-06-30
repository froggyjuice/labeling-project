# Django + ngrok HTTPS Hosting Script
# PowerShell Execution Policy: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Django + ngrok HTTPS Hosting" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check current directory
Write-Host "Current Directory: $(Get-Location)" -ForegroundColor Green

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python and try again." -ForegroundColor Red
    Read-Host "Press Enter to continue"
    exit 1
}

# Check Django installation
Write-Host "Checking Django installation..." -ForegroundColor Yellow
try {
    python -c "import django" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Django installation confirmed" -ForegroundColor Green
    } else {
        throw "Django not found"
    }
} catch {
    Write-Host "Django is not installed. Installing..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Check ngrok installation
Write-Host "Checking ngrok installation..." -ForegroundColor Yellow
$ngrokPath = ".\ngrok\ngrok.exe"
if (Test-Path $ngrokPath) {
    try {
        $ngrokVersion = & $ngrokPath version 2>$null
        Write-Host "✅ ngrok found: $ngrokVersion" -ForegroundColor Green
    } catch {
        Write-Host "❌ Error: Failed to run ngrok!" -ForegroundColor Red
        Read-Host "Press Enter to continue"
        exit 1
    }
} else {
    Write-Host "❌ Error: ngrok.exe not found!" -ForegroundColor Red
    Write-Host "If you have ngrok.zip, please extract it first:" -ForegroundColor Yellow
    Write-Host "Expand-Archive ngrok.zip" -ForegroundColor White
    Write-Host ""
    Write-Host "Or download ngrok using one of these methods:" -ForegroundColor Yellow
    Write-Host "1. Chocolatey: choco install ngrok" -ForegroundColor White
    Write-Host "2. Manual download: https://ngrok.com/download" -ForegroundColor White
    Write-Host "3. PowerShell: Invoke-WebRequest -Uri 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip' -OutFile 'ngrok.zip'" -ForegroundColor White
    Read-Host "Press Enter to continue"
    exit 1
}

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  Warning: .env file not found." -ForegroundColor Yellow
    Write-Host "Please create .env file for Google OAuth settings." -ForegroundColor Yellow
    Write-Host "Example content:" -ForegroundColor White
    Write-Host "GOOGLE_CLIENT_ID=your_client_id" -ForegroundColor Gray
    Write-Host "GOOGLE_CLIENT_SECRET=your_client_secret" -ForegroundColor Gray
    Write-Host ""
}

# Collect static files
Write-Host "Collecting static files..." -ForegroundColor Yellow
python manage.py collectstatic --noinput

# Database migration
Write-Host "Checking database migrations..." -ForegroundColor Yellow
python manage.py migrate

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Django server and ngrok tunnel..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Django server in background
Write-Host "Starting Django server (port 8000)..." -ForegroundColor Green
$djangoJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python manage.py runserver 8000
}

# Wait for server to start
Write-Host "Waiting for Django server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Check server status
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host "✅ Django server started successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Cannot verify Django server response. Continuing..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting ngrok HTTPS tunnel..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    IMPORTANT: Use the HTTPS URL below!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Start ngrok tunnel
try {
    & $ngrokPath http 8000
} catch {
    Write-Host "Error occurred while running ngrok." -ForegroundColor Red
} finally {
    # Stop Django server after ngrok exits
    Write-Host ""
    Write-Host "ngrok has exited. Stopping Django server..." -ForegroundColor Yellow
    Stop-Job -Job $djangoJob
    Remove-Job -Job $djangoJob
    Write-Host "✅ All services have been stopped." -ForegroundColor Green
}

Read-Host "Press Enter to exit" 