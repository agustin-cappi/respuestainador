@echo off
setlocal enabledelayedexpansion
title Respuestasinador - verificacion (Claude)
color 0F

echo.
echo ==========================================
echo    VERIFICANDO INSTALACION DE CLAUDE CODE
echo ==========================================
echo.

set "FAIL=0"
set "VJSON=%TEMP%\rs_verify_claude.json"
set "VERR=%TEMP%\rs_verify_claude.err"
set "CLAUDEPATH="

echo [1/4] Buscando 'claude' en el PATH...
where claude >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%A in ('where claude') do (
        if not defined CLAUDEPATH set "CLAUDEPATH=%%A"
    )
    echo       OK: !CLAUDEPATH!
) else (
    echo       NO esta en el PATH, probando rutas tipicas...
    if exist "%USERPROFILE%\.local\bin\claude.exe"       set "CLAUDEPATH=%USERPROFILE%\.local\bin\claude.exe"
    if not defined CLAUDEPATH if exist "%USERPROFILE%\.local\bin\claude.cmd"       set "CLAUDEPATH=%USERPROFILE%\.local\bin\claude.cmd"
    if not defined CLAUDEPATH if exist "%APPDATA%\npm\claude.cmd"                  set "CLAUDEPATH=%APPDATA%\npm\claude.cmd"
    if not defined CLAUDEPATH if exist "%LOCALAPPDATA%\Programs\claude\claude.exe" set "CLAUDEPATH=%LOCALAPPDATA%\Programs\claude\claude.exe"
    if defined CLAUDEPATH (
        echo       OK: !CLAUDEPATH!
    ) else (
        echo       FALTA: no se encuentra claude en ningun lado
        echo.
        echo       Para instalarlo:
        echo         1^) Instala Node.js desde https://nodejs.org
        echo         2^) Abri una terminal y corre:
        echo              npm install -g @anthropic-ai/claude-code
        echo         3^) Corre 'claude' para loguearte
        echo         4^) Volve a correr este verificar.bat
        set "FAIL=1"
        goto :end
    )
)
echo.

echo [2/4] Chequeando version...
"!CLAUDEPATH!" --version
if %errorlevel% neq 0 (
    echo       FALLO: 'claude --version' tiro error ^(ver linea de arriba^)
    set "FAIL=1"
    goto :end
)
echo.

echo [3/4] Chequeando login/autenticacion ^(prompt minimo^)...
echo       ^(puede tardar 5-15 seg la primera vez^)
"!CLAUDEPATH!" -p "responde solo: ok" --output-format json >"%VJSON%" 2>"%VERR%"
if %errorlevel% neq 0 (
    echo       FALLO: claude respondio con error
    echo       ----- stderr -----
    type "%VERR%"
    echo       ------------------
    echo.
    echo       Lo mas probable: no estas logueado. Corre:
    echo             claude
    echo       en una terminal, segui los pasos del navegador, y volve.
    set "FAIL=1"
    goto :end
)
findstr /i /c:"\"result\"" "%VJSON%" >nul
if %errorlevel% neq 0 (
    echo       RARO: no vino 'result' en la respuesta
    type "%VJSON%"
    set "FAIL=1"
    goto :end
)
echo       OK: claude responde y esta autenticado
echo.

echo [4/4] Chequeando que el .env este configurado para claude...
if not exist "%~dp0.env" (
    echo       FALTA: no hay .env al lado del exe
    set "FAIL=1"
    goto :end
)
findstr /b /i /c:"RESPUESTASINADOR_BACKEND=claude" "%~dp0.env" >nul
if %errorlevel% neq 0 (
    echo       OJO: el .env no tiene la linea activa:
    echo             RESPUESTASINADOR_BACKEND=claude
    echo       Puede estar comentada con '#' o faltar. Editala en:
    echo             %~dp0.env
    set "FAIL=1"
    goto :end
)
echo       OK: .env listo
echo.

:end
del /q "%VJSON%" >nul 2>&1
del /q "%VERR%" >nul 2>&1

echo ==========================================
if "%FAIL%"=="0" (
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
