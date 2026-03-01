@echo off
chcp 65001 > nul
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Inicializacao (Windows)
:: Fase 21 — One-Click Local Production + Chrome App Mode
::
:: USO: Duplo-clique em iniciar.bat
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT -- Iniciando ambiente local...
echo =============================================

cd /d "%~dp0"

:: Garantir que as pastas de persistencia existem
if not exist "local_data\db" mkdir "local_data\db"
if not exist "local_data\templates" mkdir "local_data\templates"
if not exist "backups" mkdir "backups"

:: Copiar o template Excel para local_data\templates se ainda nao estiver la
set TEMPLATE_SRC=backend\app\templates\modelo.xlsm
set TEMPLATE_DST=local_data\templates\modelo.xlsm

if exist "%TEMPLATE_SRC%" (
    if not exist "%TEMPLATE_DST%" (
        echo -^> Copiando template Excel para local_data\templates\...
        copy "%TEMPLATE_SRC%" "%TEMPLATE_DST%" >nul
    )
)

:: Subir os containers em modo detached
echo -^> Iniciando containers Docker...
docker compose -f docker-compose.local.yml up -d --build

:: Healthcheck: aguarda o sistema responder 200 (max 90s via PowerShell)
echo -^> Aguardando o sistema responder em http://localhost...
set ELAPSED=0
set READY=0

:WAIT_LOOP
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -Uri 'http://localhost' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -ge 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    set READY=1
    goto :OPEN_BROWSER
)
timeout /t 3 /nobreak >nul
set /a ELAPSED=%ELAPSED%+3
echo    (%ELAPSED%s) aguardando...
if %ELAPSED% lss 90 goto :WAIT_LOOP

echo [AVISO] Sistema nao respondeu em 90s. Verifique os logs:
echo         docker compose -f docker-compose.local.yml logs
goto :SHOW_INFO

:OPEN_BROWSER
:: Tenta abrir o Chrome em modo App (janela dedicada, sem barra de navegador)
set CHROME1=C:\Program Files\Google\Chrome\Application\chrome.exe
set CHROME2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
set CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe

if exist "%CHROME1%" (
    echo -^> Abrindo Chrome em modo App...
    start "" "%CHROME1%" "--app=http://localhost"
    goto :SHOW_INFO
)
if exist "%CHROME2%" (
    echo -^> Abrindo Chrome em modo App...
    start "" "%CHROME2%" "--app=http://localhost"
    goto :SHOW_INFO
)
if exist "%CHROME3%" (
    echo -^> Abrindo Chrome em modo App...
    start "" "%CHROME3%" "--app=http://localhost"
    goto :SHOW_INFO
)

:: Fallback: navegador padrao
echo -^> Abrindo navegador padrao em http://localhost...
start "" "http://localhost"

:SHOW_INFO
echo.
echo [OK] CACL LIGHT esta rodando!
echo      Aplicacao  : http://localhost
echo      API (docs) : http://localhost:8000/docs
echo      SQLite Web : http://localhost:8080
echo.
echo      Para parar (com backup automatico): parar.bat
echo      Para atualizar                    : atualizar.bat
echo =============================================
pause
