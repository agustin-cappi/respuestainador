@echo off
setlocal enabledelayedexpansion
title Respuestasinador - verificacion (Antigravity)
color 0F

echo.
echo ==========================================
echo    VERIFICANDO INSTALACION DE ANTIGRAVITY
echo ==========================================
echo.

set "FAIL=0"
set "VJSON=%TEMP%\rs_verify_agy.json"
set "VERR=%TEMP%\rs_verify_agy.err"
set "AGYPATH="

echo [1/4] Buscando 'agy' en el PATH...
where agy >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%A in ('where agy') do (
        if not defined AGYPATH set "AGYPATH=%%A"
    )
    echo       OK: !AGYPATH!
) else (
    echo       NO esta en el PATH, probando carpeta de WinGet...
    for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.AntigravityCLI_*") do (
        if not defined AGYPATH if exist "%%D\agy.exe" set "AGYPATH=%%D\agy.exe"
    )
    if not defined AGYPATH if exist "%USERPROFILE%\.local\bin\agy.exe"            set "AGYPATH=%USERPROFILE%\.local\bin\agy.exe"
    if not defined AGYPATH if exist "%APPDATA%\npm\agy.cmd"                       set "AGYPATH=%APPDATA%\npm\agy.cmd"
    if not defined AGYPATH if exist "%LOCALAPPDATA%\Programs\Antigravity\agy.exe" set "AGYPATH=%LOCALAPPDATA%\Programs\Antigravity\agy.exe"
    if defined AGYPATH (
        echo       OK: !AGYPATH!
    ) else (
        echo       FALTA: no se encuentra agy en ningun lado
        echo.
        echo       Para instalarlo:
        echo         1^) Abri PowerShell y corre:
        echo              winget install Google.AntigravityCLI
        echo            ^(o descargalo desde https://antigravity.google^)
        echo         2^) Corre 'agy' para loguearte con tu cuenta Google
        echo         3^) Volve a correr este verificar.bat
        set "FAIL=1"
        goto :end
    )
)
echo.

echo [2/4] Chequeando version...
"!AGYPATH!" --version
if %errorlevel% neq 0 (
    echo       FALLO: 'agy --version' tiro error ^(ver linea de arriba^)
    set "FAIL=1"
    goto :end
)
echo.

echo [3/4] Chequeando login/autenticacion ^(prompt minimo^)...
echo       ^(puede tardar 5-15 seg la primera vez^)
"!AGYPATH!" -p "responde solo: ok" --output-format json >"%VJSON%" 2>"%VERR%"
if %errorlevel% neq 0 (
    echo       FALLO: agy respondio con error
    echo       ----- stderr -----
    type "%VERR%"
    echo       ------------------
    echo.
    echo       Lo mas probable: no estas logueado. Corre:
    echo             agy
    echo       en una terminal, segui los pasos del navegador, y volve.
    set "FAIL=1"
    goto :end
)
findstr /i /c:"SUCCESS" "%VJSON%" >nul
if %errorlevel% neq 0 (
    echo       RARO: no vino status=SUCCESS en la respuesta
    type "%VJSON%"
    set "FAIL=1"
    goto :end
)
echo       OK: agy responde y esta autenticado
echo.

echo [4/4] Chequeando que el .env este configurado para antigravity...
if not exist "%~dp0.env" (
    echo       FALTA: no hay .env al lado del exe
    set "FAIL=1"
    goto :end
)
findstr /b /i /c:"RESPUESTASINADOR_BACKEND=antigravity" "%~dp0.env" >nul
if %errorlevel% neq 0 (
    echo       OJO: el .env no tiene la linea activa:
    echo             RESPUESTASINADOR_BACKEND=antigravity
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
