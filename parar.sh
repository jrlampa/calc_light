#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Parada Graciosa (Linux / macOS)
# Fase 21 — Auto-Backup + Graceful Stop
#
# USO: ./parar.sh
# Realiza backup automático do banco antes de parar os containers.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo "  CACL LIGHT — Parando containers..."
echo "============================================="

DB_SOURCE="./local_data/db/cacl_light.db"
BACKUP_DIR="./backups"

# Auto-backup antes de parar (protege contra corrupção na parada)
if [ -f "$DB_SOURCE" ]; then
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
    BACKUP_FILE="${BACKUP_DIR}/cacl_backup_${TIMESTAMP}.db"
    cp -p "$DB_SOURCE" "$BACKUP_FILE"
    echo "✅ Backup automático criado: $BACKUP_FILE"
else
    echo "   (Nenhum banco encontrado em $DB_SOURCE — backup ignorado)"
fi

# Parar os containers de forma graciosa
docker compose -f docker-compose.local.yml down

echo ""
echo "✅ Containers parados. Dados preservados em ./local_data/"
echo "   Backups disponíveis em: ./backups/"
echo "============================================="
