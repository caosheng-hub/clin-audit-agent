$ErrorActionPreference = "Stop"

Write-Host "== ClinAudit Agent / Ollama setup ==" -ForegroundColor Cyan

Write-Host "`n[1/4] Checking NVIDIA GPU..." -ForegroundColor Yellow
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Warning "nvidia-smi not found. Install the NVIDIA driver first."
}

Write-Host "`n[2/4] Checking Ollama..." -ForegroundColor Yellow
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama is not installed."
    Write-Host "Download and install: https://ollama.com/download/OllamaSetup.exe"
    exit 1
}
ollama --version

Write-Host "`n[3/4] Pulling Qwen2.5-7B (about 4.7 GB)..." -ForegroundColor Yellow
ollama pull qwen2.5:7b-instruct-q4_K_M

Write-Host "`n[4/4] Testing model..." -ForegroundColor Yellow
ollama run qwen2.5:7b-instruct-q4_K_M "只输出 OK"

Write-Host "`nDone. Now run from the project root:" -ForegroundColor Green
Write-Host "  python -m clinagent.cli llm-check"
