@echo off
echo Starting Medieval Fantasy MMORPG with LM Studio...
echo.

REM Set environment variables for LM Studio
set OLLAMA_URL=http://localhost:1234
set OLLAMA_MODEL=qwen3-1.7b
REM Uncomment and add your token if LM Studio requires authentication:
REM set LM_STUDIO_API_TOKEN=your-token-here

echo Configuration:
echo   LLM URL: %OLLAMA_URL%
echo   Model: %OLLAMA_MODEL%
echo.

REM Start the game server
python main.py

pause