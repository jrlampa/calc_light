@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Backup do Banco de Dados (Windows)
:: Fase 21 — Disaster Recovery Local
::
:: USO: Duplo-clique em backup_db.bat
::
:: O backup é salvo em .\backups\ com timestamp no nome.
:: Exemplo: backups\cacl_backup_2026-03-01_14-30-05.db
::
:: Requer PowerShell (disponível por padrão no Windows 7+)
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT — Backup do Banco de Dados
echo =============================================

cd /d "%~dp0"

set DB_SOURCE=local_data\db\cacl_light.db
set BACKUP_DIR=backups

:: Cria a pasta de backups se não existir
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Verifica se o banco existe
if not exist "%DB_SOURCE%" (
    echo [AVISO] Banco de dados nao encontrado em: %DB_SOURCE%
    echo         Certifique-se de que o sistema foi iniciado ao menos uma vez.
    pause
    exit /b 1
)

:: Gera timestamp confiável via PowerShell (independente do locale do Windows)
:: Formato: YYYY-MM-DD_HH-MM-SS
for /f "usebackq delims=" %%T in (
    `powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'"`
) do set TIMESTAMP=%%T

set BACKUP_FILE=%BACKUP_DIR%\cacl_backup_%TIMESTAMP%.db

:: Realiza a cópia
copy "%DB_SOURCE%" "%BACKUP_FILE%" >nul

echo.
echo [OK] Backup criado com sucesso!
echo      Arquivo: %BACKUP_FILE%
echo.
echo      Backups disponiveis em: .\%BACKUP_DIR%\
echo =============================================
echo.
echo Para restaurar um backup:
echo   1. Pare o sistema: parar.bat
echo   2. Copie o arquivo de backup para: local_data\db\cacl_light.db
echo   3. Inicie novamente: iniciar.bat
echo =============================================
pause
