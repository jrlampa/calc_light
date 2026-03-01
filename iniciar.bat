@echo off
chcp 65001 > nul
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Inicializacao (Windows)
:: Fase 21 — One-Click Local Production
::
:: USO: Duplo-clique em iniciar.bat
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT -- Iniciando ambiente local...
echo =============================================

:: Muda para o diretorio do script
cd /d "%~dp0"

:: Garantir que as pastas de persistencia existem antes de subir os containers
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

echo -^> Aguardando o sistema inicializar (15s)...
timeout /t 15 /nobreak >nul

:: Abrir o navegador padrao
echo -^> Abrindo http://localhost no navegador...
start "" "http://localhost"

echo.
echo [OK] CACL LIGHT esta rodando em: http://localhost
echo      Para parar: parar.bat
echo      Para backup: backup_db.bat
echo =============================================
pause
