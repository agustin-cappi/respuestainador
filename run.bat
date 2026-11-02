@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] creando entorno virtual...
    python -m venv .venv || goto :err
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt || goto :err
) else (
    call .venv\Scripts\activate.bat
)

if not exist ".env" (
    if exist ".env.example" (
        echo [setup] copia .env.example a .env y agrega tu ANTHROPIC_API_KEY
        pause
        exit /b 1
    )
)

python main.py
goto :eof

:err
echo [error] fallo el setup
pause
exit /b 1
