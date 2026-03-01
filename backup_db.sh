#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Backup do Banco de Dados (Linux / macOS)
# Fase 21 — Disaster Recovery Local
#
# USO: ./backup_db.sh
#
# O backup é salvo em ./backups/ com timestamp no nome.
# Exemplo: backups/cacl_backup_2026-03-01_14-30.db
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DB_SOURCE="./local_data/db/cacl_light.db"
BACKUP_DIR="./backups"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M')"
BACKUP_FILE="${BACKUP_DIR}/cacl_backup_${TIMESTAMP}.db"

echo "============================================="
echo "  CACL LIGHT — Backup do Banco de Dados"
echo "============================================="

# Verifica se o banco existe
if [ ! -f "$DB_SOURCE" ]; then
    echo "⚠️  Banco de dados não encontrado em: $DB_SOURCE"
    echo "   Certifique-se de que o sistema foi iniciado ao menos uma vez."
    exit 1
fi

# Cria a pasta de backups se não existir
mkdir -p "$BACKUP_DIR"

# Realiza a cópia com preservação de metadados
cp -p "$DB_SOURCE" "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo ""
echo "✅ Backup criado com sucesso!"
echo "   Arquivo : $BACKUP_FILE"
echo "   Tamanho : $SIZE"
echo ""

# Limpa backups antigos — mantém os 30 mais recentes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "cacl_backup_*.db" | wc -l)
if [ "$BACKUP_COUNT" -gt 30 ]; then
    EXCESS=$((BACKUP_COUNT - 30))
    echo "→ Removendo $EXCESS backup(s) antigo(s) (mantendo os 30 mais recentes)..."
    find "$BACKUP_DIR" -name "cacl_backup_*.db" -printf '%T+ %p\n' \
        | sort | head -n "$EXCESS" \
        | awk '{print $2}' | xargs rm -f
fi

echo "   Backups disponíveis em: $BACKUP_DIR/"
echo "============================================="

# Para restaurar um backup:
#   cp backups/cacl_backup_YYYY-MM-DD_HH-MM.db local_data/db/cacl_light.db
#   ./iniciar.sh
