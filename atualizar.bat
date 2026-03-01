@echo off
chcp 65001 > nul
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Atualizacao Continua (Windows)
:: Fase 21 — Developer Workflow: git pull + rebuild + restart
::
:: USO: Duplo-clique em atualizar.bat
::
:: Este script garante que o volume de dados (banco SQLite e templates)
:: seja SEMPRE preservado durante a atualizacao.
::
:: Requer PowerShell (disponivel por padrao no Windows 7+)
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT -- Atualizando sistema...
echo =============================================

cd /d "%~dp0"

set DB_SOURCE=local_data\db\cacl_light.db
set BACKUP_DIR=backups

:: 1. Backup preventivo antes de atualizar
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

if exist "%DB_SOURCE%" (
    for /f "usebackq delims=" %%T in (
        `powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`
    ) do set TIMESTAMP=%%T

    set BACKUP_FILE=%BACKUP_DIR%\cacl_backup_pre-update_%TIMESTAMP%.db
    copy "%DB_SOURCE%" "%BACKUP_FILE%" >nul
    echo [OK] Backup pre-atualizacao criado: %BACKUP_FILE%
)

:: 2. Buscar as ultimas alteracoes do repositorio
echo.
echo -^> Baixando atualizacoes (git pull)...
git pull
if %errorlevel% neq 0 (
    echo [ERRO] git pull falhou. Verifique conflitos e tente novamente.
    pause
    exit /b 1
)

:: 3. Reconstruir as imagens Docker
echo.
echo -^> Reconstruindo imagens Docker...
docker compose -f docker-compose.local.yml build
if %errorlevel% neq 0 (
    echo [ERRO] docker compose build falhou. Verifique os logs acima.
    pause
    exit /b 1
)

:: 4. Reiniciar os servicos (volumes de dados preservados automaticamente)
echo.
echo -^> Reiniciando servicos...
docker compose -f docker-compose.local.yml up -d

:: 5. Healthcheck: aguarda o sistema responder 200 (max 90s via PowerShell)
echo -^> Aguardando o sistema responder em http://localhost...
set ELAPSED=0

:WAIT_LOOP
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -Uri 'http://localhost' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -ge 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :READY
timeout /t 3 /nobreak >nul
set /a ELAPSED=%ELAPSED%+3
echo    (%ELAPSED%s) aguardando...
if %ELAPSED% lss 90 goto :WAIT_LOOP

echo [AVISO] Sistema nao respondeu em 90s apos atualizacao.
echo         Verifique: docker compose -f docker-compose.local.yml logs
goto :END

:READY
echo.
echo [OK] CACL LIGHT atualizado e rodando!
echo      Aplicacao  : http://localhost
echo      API (docs) : http://localhost:8000/docs
echo      SQLite Web : http://localhost:8080

:END
echo =============================================
pause
