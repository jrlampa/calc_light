#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Atualização Contínua (Linux / macOS)
# Fase 21 — Developer Workflow: git pull + rebuild + restart
#
# USO: ./atualizar.sh
#
# Este script garante que o volume de dados (banco SQLite e templates)
# seja SEMPRE preservado durante a atualização — nunca são perdidos.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo "  CACL LIGHT — Atualizando sistema..."
echo "============================================="

DB_SOURCE="./local_data/db/cacl_light.db"
BACKUP_DIR="./backups"

# 1. Backup preventivo antes de atualizar
if [ -f "$DB_SOURCE" ]; then
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
    BACKUP_FILE="${BACKUP_DIR}/cacl_backup_pre-update_${TIMESTAMP}.db"
    cp -p "$DB_SOURCE" "$BACKUP_FILE"
    echo "✅ Backup pré-atualização criado: $BACKUP_FILE"
fi

# 2. Buscar as últimas alterações do repositório
echo ""
echo "→ Baixando atualizações (git pull)..."
git pull

# 3. Reconstruir as imagens Docker com o novo código
echo ""
echo "→ Reconstruindo imagens Docker..."
docker compose -f docker-compose.local.yml build

# 4. Reiniciar os serviços (os volumes de dados são preservados automaticamente)
echo ""
echo "→ Reiniciando serviços..."
docker compose -f docker-compose.local.yml up -d

# 5. Healthcheck: aguarda o sistema responder 200 (máx 90s)
echo "→ Aguardando o sistema responder em http://localhost..."
MAX_WAIT=90
ELAPSED=0
while [ "$ELAPSED" -lt "$MAX_WAIT" ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "304" ]; then
        echo ""
        echo "✅ CACL LIGHT atualizado e rodando!"
        echo "   Aplicação  : http://localhost"
        echo "   API (docs) : http://localhost:8000/docs"
        echo "   SQLite Web : http://localhost:8080"
        echo "============================================="
        exit 0
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo "   ($ELAPSED s) aguardando..."
done

echo ""
echo "⚠️  Sistema não respondeu em ${MAX_WAIT}s após atualização."
echo "   Verifique: docker compose -f docker-compose.local.yml logs"
echo "============================================="
exit 1
