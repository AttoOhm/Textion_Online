# Start Medieval Fantasy MMORPG with LM Studio
Write-Host "Starting Medieval Fantasy MMORPG with LM Studio..." -ForegroundColor Cyan
Write-Host ""

# Set environment variables for LM Studio
$env:OLLAMA_URL = "http://localhost:1234"
$env:OLLAMA_MODEL = "qwen3-8b"
# Uncomment and add your token if LM Studio requires authentication:
# $env:LM_STUDIO_API_TOKEN = "your-token-here"

Write-Host "Configuration:"
Write-Host "  LLM URL: $env:OLLAMA_URL"
Write-Host "  Model: $env:OLLAMA_MODEL"
Write-Host "  API Token: $(if ($env:LM_STUDIO_API_TOKEN) { 'Set' } else { 'Not set' })"
Write-Host ""

# Start the game server
Write-Host "Starting game server..." -ForegroundColor Green
python main.py

Read-Host "Press Enter to exit"