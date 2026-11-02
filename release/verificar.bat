@echo off
setlocal enabledelayedexpansion
title Respuestasinador - verificacion (Claude)
color 0F

echo.
echo ==========================================
echo    VERIFICANDO INSTALACION DE CLAUDE CODE
echo ==========================================
echo.

set FAIL=0

echo [1/4] Buscando 'claude' en el PATH...
where claude >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%A in ('where claude') do set CLAUDEPATH=%%A
    echo       OK: !CLAUDEPATH!
) else (
    echo       NO esta en el PATH, probando rutas tipicas...
    set FOUND=
    if exist "%USERPROFILE%\.local\bin\claude.exe" set FOUND=%USERPROFILE%\.local\bin\claude.exe
    if exist "%USERPROFILE%\.local\bin\claude.cmd" set FOUND=%USERPROFILE%\.local\bin\claude.cmd
    if exist "%APPDATA%\npm\claude.cmd" set FOUND=%APPDATA%\npm\claude.cmd
    if exist "%LOCALAPPDATA%\Programs\claude\claude.exe" set FOUND=%LOCALAPPDATA%\Programs\claude\claude.exe
    if defined FOUND (
        echo       OK: !FOUND!
        set CLAUDEPATH=!FOUND!
    ) else (
        echo       FALTA: no se encuentra claude en ningun lado
        echo.
        echo       Para instalarlo:
        echo         1^) Instala Node.js desde https://nodejs.org
        echo         2^) Abri una terminal y corre:
        echo              npm install -g @anthropic-ai/claude-code
        echo         3^) Volve a correr este verificar.bat
        set FAIL=1
        goto :end
    )
)
echo.

echo [2/4] Chequeando version...
"!CLAUDEPATH!" --version 2>nul
if %errorlevel% neq 0 (
    echo       FALTA: 'claude --version' fallo
    set FAIL=1
    goto :end
)
echo.

echo [3/4] Chequeando login/autenticacion ^(prompt minimo^)...
echo       ^(puede tardar 5-15 seg la primera vez^)
"!CLAUDEPATH!" -p "responde solo: ok" --output-format json >"%TEMP%\rs_verify.json" 2>"%TEMP%\rs_verify.err"
if %errorlevel% neq 0 (
    echo       FALLO: claude respondio con error
    echo       ----- stderr -----
    type "%TEMP%\rs_verify.err"
    echo       ------------------
    echo.
    echo       Lo mas probable: no estas logueado. Corre:
    echo             claude
    echo       en una terminal, segui los pasos del navegador, y volve.
    set FAIL=1
    goto :end
)
findstr /i "\"result\"" "%TEMP%\rs_verify.json" >nul
if %errorlevel% neq 0 (
    echo       RARO: no vino 'result' en la respuesta
    type "%TEMP%\rs_verify.json"
    set FAIL=1
    goto :end
)
echo       OK: claude responde y esta autenticado
echo.

echo [4/4] Chequeando que el .env este configurado para claude...
if not exist "%~dp0.env" (
    echo       FALTA: no hay .env al lado del exe
    set FAIL=1
    goto :end
)
findstr /i /c:"RESPUESTASINADOR_BACKEND=claude" "%~dp0.env" >nul
if %errorlevel% neq 0 (
    echo       OJO: el .env no dice RESPUESTASINADOR_BACKEND=claude
    echo       Editalo y asegurate que esa linea este activa.
    set FAIL=1
    goto :end
)
echo       OK: .env listo
echo.

:end
echo ==========================================
if %FAIL% equ 0 (
    color 2F
    echo    TODO BIEN - podes correr respuestasinador.exe
) else (
    color 4F
    echo    HAY ALGO QUE ARREGLAR ^(mira arriba^)
)
echo ==========================================
echo.
pause
endlocal
