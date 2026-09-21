$ErrorActionPreference = "Stop"

# Start the inbox server locally without Docker.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir = Join-Path $ProjectRoot "server"

Set-Location $ServerDir

# Equivalent to the environment configured in docker-compose.yml / Dockerfile.
$env:DATA_DIR = Join-Path $ProjectRoot "data_v2"
$env:GROUND_TRUTH = Join-Path $ProjectRoot "data_v2\ground_truth.json"
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
$env:CLASSIFIER_MODEL_PATH = Join-Path $ProjectRoot "models\random_forest_classifier.joblib"
$env:EMBEDDING_MODEL = Join-Path $ProjectRoot "models\all-MiniLM-L6-v2"
$env:HF_HUB_OFFLINE = "1"

if (-not (Test-Path $env:GROUND_TRUTH)) {
    Write-Error "Missing ground-truth file: $env:GROUND_TRUTH"
}

if (-not (Test-Path $env:CLASSIFIER_MODEL_PATH)) {
    Write-Error "Missing classifier model: $env:CLASSIFIER_MODEL_PATH"
}

Write-Host "Starting inbox server at http://localhost:8000"
Write-Host "Data directory: $env:DATA_DIR"

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
