"""Motor de exportação em lotes paginados para planilhas xlsm.

Regras de negócio:
- Um arquivo ``poste_XX.xlsm`` por poste (sequencial com zero-padding de 2 dígitos).
- Máximo de 30 arquivos por lote.  Se houver mais de 30 postes o ZIP conterá
  subpastas ``Lote_01/``, ``Lote_02/``, etc.
- openpyxl com ``keep_vba=True`` para preservar macros e estrutura binária.
- Apenas os inputs brutos são injetados; os cálculos ficam com a planilha.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import openpyxl

from app.domain.excel_mapping import CALC_SHEET, CELL_MAP

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "modelo.xlsm"
BATCH_SIZE = 30


def _inject_data(ws: Any, data: dict[str, Any]) -> None:
    """Escreve cada campo do dicionário ``data`` na célula mapeada em CELL_MAP.

    Campos ausentes no dicionário são silenciosamente ignorados (mantém o
    valor original da planilha modelo).
    """
    for field, cell_ref in CELL_MAP.items():
        if field in data and data[field] is not None:
            ws[cell_ref] = data[field]


def build_poste_xlsm(data: dict[str, Any], template_path: Path = TEMPLATE_PATH) -> bytes:
    """Gera os bytes de um arquivo .xlsm com os dados de um único poste.

    Args:
        data: Dicionário cujas chaves correspondem a ``CELL_MAP`` (ex.: ``modelo_poste``, ``mt1_t1_vao``).
        template_path: Caminho para o arquivo modelo.xlsm.

    Returns:
        Bytes do arquivo .xlsm gerado.
    """
    wb = openpyxl.load_workbook(template_path, keep_vba=True)
    ws = wb[CALC_SHEET]
    _inject_data(ws, data)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_export_zip(
    postes_data: list[dict[str, Any]],
    template_path: Path = TEMPLATE_PATH,
) -> bytes:
    """Gera um ZIP mestre contendo os arquivos xlsm em lotes de até ``BATCH_SIZE`` arquivos.

    Estrutura do ZIP:
    - Se total ≤ BATCH_SIZE: arquivos na raiz.
    - Se total > BATCH_SIZE: pastas ``Lote_01/``, ``Lote_02/``, etc.

    O nome de cada arquivo segue o padrão ``poste_XX.xlsm`` (zero-padded 2 dígitos,
    estendido automaticamente para 3+ se necessário).

    Args:
        postes_data: Lista de dicionários, um por poste, com os campos de CELL_MAP.
        template_path: Caminho para o arquivo modelo.xlsm.

    Returns:
        Bytes do arquivo ZIP.
    """
    total = len(postes_data)
    pad = max(2, len(str(total)))
    use_batches = total > BATCH_SIZE

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, data in enumerate(postes_data, start=1):
            filename = f"poste_{str(idx).zfill(pad)}.xlsm"
            xlsm_bytes = build_poste_xlsm(data, template_path=template_path)

            if use_batches:
                lote_num = (idx - 1) // BATCH_SIZE + 1
                arcname = f"Lote_{str(lote_num).zfill(2)}/{filename}"
            else:
                arcname = filename

            zf.writestr(arcname, xlsm_bytes)

    return zip_buf.getvalue()
