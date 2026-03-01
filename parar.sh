#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CACL LIGHT — Script de Parada Graciosa (Linux / macOS)
# Fase 21 — One-Click Local Production
#
# USO: ./parar.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo "  CACL LIGHT — Parando containers..."
echo "============================================="

docker compose -f docker-compose.local.yml down

echo ""
echo "✅ Containers parados. Dados preservados em ./local_data/"
echo "============================================="
