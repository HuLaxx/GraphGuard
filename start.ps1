# GraphGuard - Local Launcher
# Run: .\start.ps1

param(
    [switch]$SkipDocker,
    [switch]$SkipSeed,
    [switch]$SkipInstall,
    [switch]$SkipApi,
    [switch]$SkipFrontend,
    [switch]$StartStream,
    [double]$StreamIntervalSec = 5
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
Set-Location -Path $projectRoot
$pythonPath = Join-Path $projectRoot ".venv311\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Load-EnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        $pair = $line -split "=", 2
        if ($pair.Length -ne 2) { return }
        $name = $pair[0].Trim()
        $value = $pair[1].Trim()
        if (-not $name) { return }
        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Trim('"')
        }
        if ($value.StartsWith("'") -and $value.EndsWith("'")) {
            $value = $value.Trim("'")
        }
        if (-not (Test-Path "env:$name")) {
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

Write-Host "GraphGuard Local Launcher" -ForegroundColor Cyan
Write-Host "Root: $projectRoot" -ForegroundColor DarkGray

$envPath = Join-Path $projectRoot ".env"
$envExamplePath = Join-Path $projectRoot ".env.example"
if (-not (Test-Path $envPath) -and (Test-Path $envExamplePath)) {
    Copy-Item $envExamplePath $envPath
    Write-Host "Created .env from .env.example (defaults)." -ForegroundColor Yellow
}

Load-EnvFile $envPath

$neo4jUri = $env:NEO4J_URI
if (-not $neo4jUri) { $neo4jUri = "bolt://127.0.0.1:7687" }

$neo4jUser = $env:NEO4J_USER
$neo4jPassword = $env:NEO4J_PASSWORD

if ((-not $neo4jUser) -or (-not $neo4jPassword)) {
    if ($env:NEO4J_AUTH -and $env:NEO4J_AUTH -match "^(?<user>[^/]+)/(?<pass>.+)$") {
        if (-not $neo4jUser) { $neo4jUser = $Matches.user }
        if (-not $neo4jPassword) { $neo4jPassword = $Matches.pass }
    }
}

if (-not $neo4jUser) { $neo4jUser = "neo4j" }
if (-not $neo4jPassword) { $neo4jPassword = "graphguard_dev" }

$apiKey = $env:API_KEY
if (-not $apiKey) { $apiKey = "change-me" }
if ($apiKey -eq "change-me") {
    Write-Host "API_KEY is still change-me; protected mutations will fail until updated." -ForegroundColor Yellow
}

Set-Item -Path env:NEO4J_URI -Value $neo4jUri
Set-Item -Path env:NEO4J_USER -Value $neo4jUser
Set-Item -Path env:NEO4J_PASSWORD -Value $neo4jPassword
Set-Item -Path env:API_KEY -Value $apiKey
Set-Item -Path env:NEXT_PUBLIC_API_PORT -Value "8000"
Set-Item -Path env:API_PORT -Value "8000"
Set-Item -Path env:NEXT_PUBLIC_API_KEY -Value $apiKey

$dockerReady = $false
if (-not $SkipDocker) {
    if (-not (Test-Command "docker")) {
        Write-Host "Docker not found; skipping Docker and seed steps." -ForegroundColor Yellow
        $SkipDocker = $true
        $SkipSeed = $true
    } else {
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker is not running; skipping Docker and seed steps." -ForegroundColor Yellow
            $SkipDocker = $true
            $SkipSeed = $true
        } else {
            $dockerReady = $true
        }
    }
}

if (-not $SkipDocker) {
    Write-Host "Starting Docker stack..." -ForegroundColor Yellow
    docker compose up -d --build
}

if (-not $SkipSeed) {
    if (-not $dockerReady) {
        Write-Host "Docker not ready; skipping seed." -ForegroundColor Yellow
    } else {
        Write-Host "Waiting for Neo4j..." -ForegroundColor Yellow
    $timeoutSec = 120
    $start = Get-Date
    $ready = $false
    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
        docker exec graphguard-neo4j cypher-shell -u $neo4jUser -p $neo4jPassword "RETURN 1;" *> $null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 3
    }

    if (-not $ready) {
        Write-Host "Neo4j did not become ready in time. Skipping seed." -ForegroundColor Red
    } else {
        Write-Host "Seeding Neo4j data..." -ForegroundColor Yellow
        & $pythonPath "data-eng\neo4j\load_graph.py"
        & $pythonPath "data-eng\neo4j\compute_basic_features.py"
    }
    }
}

if (-not $SkipInstall) {
    if (-not (Test-Command "npm")) {
        Write-Host "npm not found; skipping frontend install and start." -ForegroundColor Yellow
        $SkipInstall = $true
        $SkipFrontend = $true
    }
    $nodeModules = Join-Path $projectRoot "frontend\node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        npm --prefix frontend install
    }
}

if (-not $SkipApi) {
    if (($pythonPath -eq "python") -and (-not (Test-Command "python"))) {
        Write-Host "Python not found; skipping API start." -ForegroundColor Red
        $SkipApi = $true
    }
}

function Wait-ForApi {
    param(
        [string]$Url = "http://127.0.0.1:8000/health",
        [int]$TimeoutSec = 45
    )
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSec) {
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

if (-not $SkipApi) {
$apiCmd = @'
$env:NEO4J_URI="{0}"
$env:NEO4J_USER="{1}"
$env:NEO4J_PASSWORD="{2}"
$env:API_KEY="{3}"
& "{4}" -m uvicorn ml.serving.api:app --host 127.0.0.1 --port 8000 --reload
'@ -f $neo4jUri, $neo4jUser, $neo4jPassword, $apiKey, $pythonPath

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd -WorkingDirectory $projectRoot
    Write-Host "API started in a new window." -ForegroundColor Green
}

if (-not $SkipFrontend) {
    if (-not $SkipApi) {
        if (-not (Wait-ForApi)) {
            Write-Host "API did not respond yet; frontend will still start." -ForegroundColor Yellow
        }
    }
$frontCmd = @'
$env:NEXT_PUBLIC_API_PORT="8000"
$env:API_PORT="8000"
$env:NEXT_PUBLIC_API_KEY="{0}"
npm --prefix frontend run dev
'@ -f $apiKey

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontCmd -WorkingDirectory $projectRoot
    Write-Host "Frontend started in a new window." -ForegroundColor Green
}

if ($StartStream) {
    $streamConsumerCmd = @'
$env:API_KEY="{0}"
$env:NEO4J_URI="{1}"
$env:NEO4J_USER="{2}"
$env:NEO4J_PASSWORD="{3}"
& "{4}" streaming_consumer.py
'@ -f $apiKey, $neo4jUri, $neo4jUser, $neo4jPassword, $pythonPath

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $streamConsumerCmd -WorkingDirectory $projectRoot
    Write-Host "Live stream consumer started." -ForegroundColor Green

    $streamProducerCmd = @'
& "{0}" streaming_producer.py --interval {1}
'@ -f $pythonPath, $StreamIntervalSec

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $streamProducerCmd -WorkingDirectory $projectRoot
    Write-Host "Live stream producer started." -ForegroundColor Green
}

Write-Host "Open: http://localhost:3000/demo" -ForegroundColor Cyan
