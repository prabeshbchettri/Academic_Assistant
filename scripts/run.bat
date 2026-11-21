@echo off
cd /d "%~dp0\.."

where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo uv is required but not installed. Please install uv: https://github.com/astral-sh/uv
    exit /b 1
)

echo Launching Academic Assistant Desktop Application...
uv run python -m app.main %*
