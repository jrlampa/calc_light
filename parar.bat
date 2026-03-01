@echo off
chcp 65001 > nul
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Parada Graciosa (Windows)
:: Fase 21 — Auto-Backup + Graceful Stop
::
:: USO: Duplo-clique em parar.bat
:: Realiza backup automatico do banco antes de parar os containers.
::
:: Requer PowerShell (disponivel por padrao no Windows 7+)
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT -- Parando containers...
echo =============================================

cd /d "%~dp0"

set DB_SOURCE=local_data\db\cacl_light.db
set BACKUP_DIR=backups

:: Cria a pasta de backups se nao existir
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Auto-backup antes de parar (protege contra corrupcao na parada)
if exist "%DB_SOURCE%" (
    :: Gera timestamp confiavel via PowerShell (independente do locale do Windows)
    for /f "usebackq delims=" %%T in (
        `powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`
    ) do set TIMESTAMP=%%T

    set BACKUP_FILE=%BACKUP_DIR%\cacl_backup_%TIMESTAMP%.db
    copy "%DB_SOURCE%" "%BACKUP_FILE%" >nul
    echo [OK] Backup automatico criado: %BACKUP_FILE%
) else (
    echo     (Nenhum banco encontrado em %DB_SOURCE% -- backup ignorado)
)

:: Parar os containers de forma graciosa
docker compose -f docker-compose.local.yml down

echo.
echo [OK] Containers parados. Dados preservados em .\local_data\
echo      Backups disponiveis em: .\backups\
echo =============================================
pause
