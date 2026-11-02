@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] creando entorno virtual...
    python -m venv .venv || goto :err
)

call .venv\Scripts\activate.bat

echo [setup] instalando dependencias...
pip install --upgrade pip >nul
pip install -r requirements.txt || goto :err
pip install pyinstaller>=6.0 || goto :err

echo [build] limpiando outputs previos...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [build] compilando .exe...
pyinstaller --clean --noconfirm respuestasinador.spec || goto :err

if exist "dist\respuestasinador.exe" (
    copy /y ".env.example" "dist\.env.example" >nul
    echo.
    echo [ok] binario listo en: dist\respuestasinador.exe
    echo      no necesita API key, usa el claude CLI que ya tenes instalado
    echo.
) else (
    echo [error] no se genero el exe
    goto :err
)

goto :eof

:err
echo [error] fallo el build
pause
exit /b 1
