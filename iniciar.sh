#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Inicialização (Linux / macOS)
# Fase 21 — One-Click Local Production + Chrome App Mode
#
# USO: ./iniciar.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo "  CACL LIGHT — Iniciando ambiente local..."
echo "============================================="

# Garantir que as pastas de persistência existem
mkdir -p ./local_data/db
mkdir -p ./local_data/templates
mkdir -p ./backups

# Copiar o template Excel para local_data/templates se ainda não estiver lá
TEMPLATE_SRC="./backend/app/templates/modelo.xlsm"
TEMPLATE_DST="./local_data/templates/modelo.xlsm"

if [ -f "$TEMPLATE_SRC" ] && [ ! -f "$TEMPLATE_DST" ]; then
    echo "→ Copiando template Excel para local_data/templates/..."
    cp "$TEMPLATE_SRC" "$TEMPLATE_DST"
fi

# Subir os containers em modo detached
echo "→ Iniciando containers Docker..."
docker compose -f docker-compose.local.yml up -d --build

# Healthcheck: aguarda o sistema responder 200 (máx 90s)
echo "→ Aguardando o sistema responder em http://localhost..."
MAX_WAIT=90
ELAPSED=0
READY=0
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        READY=1
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo "   ($ELAPSED s) aguardando..."
done

if [ "$READY" -eq 0 ]; then
    echo "⚠️  Sistema não respondeu em ${MAX_WAIT}s. Verifique: docker compose -f docker-compose.local.yml logs"
fi

# Abrir o navegador — tenta Chrome/Chromium em modo --app (sem barra de navegação)
URL="http://localhost"
echo "→ Abrindo $URL..."
OPENED=0

if command -v google-chrome &>/dev/null; then
    google-chrome --app="$URL" &>/dev/null &
    OPENED=1
elif command -v google-chrome-stable &>/dev/null; then
    google-chrome-stable --app="$URL" &>/dev/null &
    OPENED=1
elif command -v chromium-browser &>/dev/null; then
    chromium-browser --app="$URL" &>/dev/null &
    OPENED=1
elif command -v chromium &>/dev/null; then
    chromium --app="$URL" &>/dev/null &
    OPENED=1
elif command -v open &>/dev/null; then
    # macOS — tenta Chrome primeiro
    if [ -d "/Applications/Google Chrome.app" ]; then
        open -a "Google Chrome" --args --app="$URL"
    else
        open "$URL"
    fi
    OPENED=1
elif command -v xdg-open &>/dev/null; then
    xdg-open "$URL" &
    OPENED=1
fi

if [ "$OPENED" -eq 0 ]; then
    echo "  (Não foi possível abrir o navegador automaticamente. Acesse: $URL)"
fi

echo ""
echo "✅ CACL LIGHT está rodando!"
echo "   Aplicação  : http://localhost"
echo "   API (docs) : http://localhost:8000/docs"
echo "   SQLite Web : http://localhost:8080"
echo ""
echo "   Para parar (com backup automático): ./parar.sh"
echo "   Para atualizar                    : ./atualizar.sh"
echo "============================================="
