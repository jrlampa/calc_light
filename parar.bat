@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: CACL LIGHT — Script de Parada Graciosa (Windows)
:: Fase 21 — One-Click Local Production
::
:: USO: Duplo-clique em parar.bat
:: ─────────────────────────────────────────────────────────────────────────────

echo =============================================
echo   CACL LIGHT — Parando containers...
echo =============================================

cd /d "%~dp0"

docker compose -f docker-compose.local.yml down

echo.
echo [OK] Containers parados. Dados preservados em .\local_data\
echo =============================================
pause
