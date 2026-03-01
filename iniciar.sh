#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Inicialização (Linux / macOS)
# Fase 21 — One-Click Local Production
#
# USO: ./iniciar.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo "  CACL LIGHT — Iniciando ambiente local..."
echo "============================================="

# Garantir que as pastas de persistência existem antes de subir os containers
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

echo "→ Aguardando o sistema inicializar (15s)..."
sleep 15

# Abrir o navegador padrão
URL="http://localhost"
echo "→ Abrindo $URL no navegador..."
if command -v xdg-open &>/dev/null; then
    xdg-open "$URL" &
elif command -v open &>/dev/null; then
    # macOS
    open "$URL"
else
    echo "  (Não foi possível abrir o navegador automaticamente. Acesse: $URL)"
fi

echo ""
echo "✅ CACL LIGHT está rodando em: $URL"
echo "   Para parar: ./parar.sh"
echo "   Para backup: ./backup_db.sh"
echo "============================================="
