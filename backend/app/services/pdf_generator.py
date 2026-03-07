"""
pdf_generator.py — Fase 24
Gera o Memorial de Cálculo Técnico em PDF para entrega à concessionária.

Tecnologia: ReportLab Platypus (puro Python, sem dependências de sistema).
Entrada: metadados do projeto + CqtOutputSchema do motor elétrico V8.
Saída: bytes do PDF, prontos para StreamingResponse.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.electrical_models import CqtOutputSchema, TrechoResultSchema

# ── Paleta de Cores — Identidade Visual de Engenharia ──────────────────────

NAVY       = colors.HexColor("#0F2B5B")   # Azul navy — cabeçalhos principais
STEEL_BLUE = colors.HexColor("#1E4D8C")   # Azul aço — sub-cabeçalhos de seção
LIGHT_BLUE = colors.HexColor("#D6E4F5")   # Azul claro — detalhe de cabeçalho
WHITE      = colors.white
DARK_GRAY  = colors.HexColor("#2D3748")   # Texto principal
MID_GRAY   = colors.HexColor("#718096")   # Texto secundário
LIGHT_GRAY = colors.HexColor("#EDF2F7")   # Fundo linhas ímpares
ROW_WHITE  = colors.HexColor("#FFFFFF")   # Fundo linhas pares

GREEN_OK   = colors.HexColor("#276749")   # Verde escuro — texto Ok
GREEN_BG   = colors.HexColor("#C6F6D5")   # Verde claro — fundo Ok
RED_FAIL   = colors.HexColor("#9B2C2C")   # Vermelho escuro — Reprovado
RED_BG     = colors.HexColor("#FED7D7")   # Vermelho claro — fundo Reprovado
AMBER_WARN = colors.HexColor("#744210")   # Âmbar — texto Atenção
AMBER_BG   = colors.HexColor("#FEEBC8")   # Âmbar claro — fundo Atenção
BORDER     = colors.HexColor("#CBD5E0")   # Grade das tabelas


# ── Estilos Tipográficos ────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle", parent=base["Normal"],
            fontSize=15, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=TA_CENTER, spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=STEEL_BLUE, alignment=TA_CENTER, spaceAfter=2,
        ),
        "meta_label": ParagraphStyle(
            "MetaLabel", parent=base["Normal"],
            fontSize=8.5, fontName="Helvetica-Bold", textColor=DARK_GRAY,
        ),
        "meta_value": ParagraphStyle(
            "MetaValue", parent=base["Normal"],
            fontSize=8.5, fontName="Helvetica", textColor=STEEL_BLUE,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=WHITE, backColor=NAVY,
            alignment=TA_LEFT, leftIndent=6,
            spaceBefore=10, spaceAfter=0, leading=20,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"],
            fontSize=7, fontName="Helvetica",
            textColor=MID_GRAY, alignment=TA_LEFT, spaceAfter=2,
        ),
        "empty_msg": ParagraphStyle(
            "EmptyMsg", parent=base["Normal"],
            fontSize=8.5, fontName="Helvetica-Oblique",
            textColor=MID_GRAY, leftIndent=6, spaceAfter=8,
        ),
    }


def _hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=STEEL_BLUE, spaceAfter=4, spaceBefore=2)


def _section_title(text: str, styles: dict) -> Paragraph:
    return Paragraph(f"&nbsp;&nbsp;{text}", styles["section_header"])


# ── Utilitários ─────────────────────────────────────────────────────────────

def _format_date(raw: str) -> str:
    """Converte data ISO/SQLite → DD/MM/YYYY HH:MM, com fallback tolerante."""
    if not raw:
        return "—"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return raw


# ── Bloco de Cabeçalho ──────────────────────────────────────────────────────

def _build_header_block(
    project_name: str,
    created_at: str,
    trafo_nominal_kva: float,
    styles: dict,
) -> list:
    elements: list = []

    elements.append(Paragraph("MEMORIAL DE CÁLCULO", styles["title"]))
    elements.append(
        Paragraph(
            "Queda de Tensão e Curto-Circuito — Rede de Baixa Tensão (Light)",
            styles["subtitle"],
        )
    )
    elements.append(Spacer(1, 5 * mm))
    elements.append(_hr())
    elements.append(Spacer(1, 3 * mm))

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    formatted_date = _format_date(created_at)

    meta_data = [
        [
            Paragraph("Projeto:", styles["meta_label"]),
            Paragraph(project_name, styles["meta_value"]),
            Paragraph("Gerado em:", styles["meta_label"]),
            Paragraph(generated_at, styles["meta_value"]),
        ],
        [
            Paragraph("Data de Criação:", styles["meta_label"]),
            Paragraph(formatted_date, styles["meta_value"]),
            Paragraph("Transformador:", styles["meta_label"]),
            Paragraph(f"{trafo_nominal_kva:.1f} kVA", styles["meta_value"]),
        ],
        [
            Paragraph("Norma de Referência:", styles["meta_label"]),
            Paragraph("NTC 905200 / NTC 905100 (Light)", styles["meta_value"]),
            Paragraph("", styles["meta_label"]),
            Paragraph("", styles["meta_value"]),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[3.5 * cm, 7.0 * cm, 3.2 * cm, 5.8 * cm])
    meta_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("SPAN",          (1, 2), (3, 2)),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6 * mm))
    return elements


# ── Resumo do Transformador ─────────────────────────────────────────────────

def _build_trafo_summary(
    cqt: CqtOutputSchema,
    trafo_nominal_kva: float,
    styles: dict,
) -> list:
    elements: list = []
    elements.append(_section_title("1. RESUMO DO TRANSFORMADOR", styles))
    elements.append(Spacer(1, 3 * mm))

    status_ok = "Sobrecarga" not in cqt.trafo_status
    status_fg = GREEN_OK if status_ok else RED_FAIL
    status_bg = GREEN_BG if status_ok else RED_BG

    margem_kva = cqt.carga_projetada_kva - cqt.carga_atual_kva

    # Cabeçalho + 4 linhas de dados
    data = [
        ["Parâmetro", "Valor", "Parâmetro", "Valor"],
        ["Potência Nominal (kVA)", f"{trafo_nominal_kva:.1f} kVA",
         "Margem de Crescimento", "15%"],
        ["Carga Atual (kVA)", f"{cqt.carga_atual_kva:.2f} kVA",
         "Reserva (15%)", f"+{margem_kva:.2f} kVA"],
        ["Carga Projetada (kVA)", f"{cqt.carga_projetada_kva:.2f} kVA",
         "Carregamento Projetado", f"{cqt.trafo_loading_percent:.1f} %"],
        ["Status do Transformador", cqt.trafo_status, "", ""],
    ]

    col_widths = [5.0 * cm, 4.5 * cm, 5.0 * cm, 4.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Cabeçalho
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        # Labels (coluna 0 e coluna 2) em negrito
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (2, 1), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("ALIGN",         (3, 0), (3, -1), "CENTER"),
        # Linha de status — span colunas 1-3
        ("BACKGROUND",    (0, 4), (-1, 4), status_bg),
        ("TEXTCOLOR",     (1, 4), (3, 4), status_fg),
        ("FONTNAME",      (1, 4), (3, 4), "Helvetica-Bold"),
        ("ALIGN",         (1, 4), (3, 4), "CENTER"),
        ("SPAN",          (1, 4), (3, 4)),
        # Grade
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.0, NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]

    # Fundo alternado nas linhas de dados (1-3)
    for row_idx in range(1, 4):
        bg = LIGHT_GRAY if row_idx % 2 == 1 else ROW_WHITE
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    return elements


# ── Tabela de Trechos ───────────────────────────────────────────────────────

def _build_trecho_table(
    trechos: list[TrechoResultSchema],
    lado_label: str,
    section_num: int,
    styles: dict,
) -> list:
    elements: list = []
    elements.append(_section_title(f"{section_num}. RESULTADOS — {lado_label.upper()}", styles))
    elements.append(Spacer(1, 3 * mm))

    if not trechos:
        elements.append(
            Paragraph(
                f"Nenhum trecho calculado para o {lado_label}.",
                styles["empty_msg"],
            )
        )
        elements.append(Spacer(1, 4 * mm))
        return elements

    # Cabeçalhos (largura total ≈ 17.5 cm — cabe em A4 retrato com margens de 1.5 cm)
    headers = [
        "Nó / Poste",
        "Carga\n(kVA)",
        "Carga Acum.\n(kVA)",
        "ΔV%\nTrecho",
        "ΔV%\nAcum.",
        "V Final\n(V)",
        "Icc\n(kA)",
        "Temp.\n(°C)",
        "Térmico",
        "Tensão",
    ]

    col_widths = [
        3.2 * cm,  # Nó/Poste
        1.7 * cm,  # Carga kVA
        2.0 * cm,  # Carga Acum.
        1.7 * cm,  # ΔV% Trecho
        1.7 * cm,  # ΔV% Acum.
        1.8 * cm,  # V Final
        1.6 * cm,  # Icc kA
        1.6 * cm,  # Temp
        1.9 * cm,  # Térmico
        1.8 * cm,  # Tensão
    ]

    table_data = [headers]
    for t in trechos:
        icc_ka = t.icc_amperes / 1000.0
        thermal_str = "Ok" if t.thermal_status == "Ok !" else "Reprovado"
        tension_str = "Ok" if t.status == "Ok" else "Atenção"
        table_data.append([
            t.id,
            f"{t.carga_kva:.2f}",
            f"{t.carga_acum_kva:.2f}",
            f"{t.dv_trecho_perc:.2f}",
            f"{t.dv_acum_perc:.2f}",
            f"{t.v_final:.1f}",
            f"{icc_ka:.3f}",
            f"{t.cable_temp_celsius:.1f}",
            thermal_str,
            tension_str,
        ])

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    THERMAL_COL = 8
    TENSION_COL = 9
    DV_ACUM_COL = 4

    style_cmds = [
        # Cabeçalho
        ("BACKGROUND",    (0, 0), (-1, 0), STEEL_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.0, NAVY),
        # Célula do nó: alinhamento à esquerda, negrito
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("ALIGN",         (0, 1), (0, -1), "LEFT"),
        # Dados numéricos: centro
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 7.5),
        ("FONTNAME",      (1, 1), (-1, -1), "Helvetica"),
        # Grade
        ("GRID",          (0, 0), (-1, -1), 0.35, BORDER),
        ("VALIGN",        (0, 1), (-1, -1), "MIDDLE"),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]

    # 1. Fundo alternado nas linhas de dados (deve vir antes das cores condicionais)
    for row_idx in range(1, len(table_data)):
        bg = LIGHT_GRAY if row_idx % 2 == 1 else ROW_WHITE
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

    # 2. Cores condicionais (sobrescrevem o fundo alternado)
    for row_idx, t in enumerate(trechos, start=1):
        thermal_ok = t.thermal_status == "Ok !"
        tension_ok = t.status == "Ok"

        # Coluna Térmico
        style_cmds.extend([
            ("BACKGROUND", (THERMAL_COL, row_idx), (THERMAL_COL, row_idx),
             GREEN_BG if thermal_ok else RED_BG),
            ("TEXTCOLOR",  (THERMAL_COL, row_idx), (THERMAL_COL, row_idx),
             GREEN_OK if thermal_ok else RED_FAIL),
            ("FONTNAME",   (THERMAL_COL, row_idx), (THERMAL_COL, row_idx),
             "Helvetica-Bold"),
        ])

        # Coluna Tensão
        if tension_ok:
            t_bg, t_fg = GREEN_BG, GREEN_OK
        else:
            t_bg, t_fg = AMBER_BG, AMBER_WARN
        style_cmds.extend([
            ("BACKGROUND", (TENSION_COL, row_idx), (TENSION_COL, row_idx), t_bg),
            ("TEXTCOLOR",  (TENSION_COL, row_idx), (TENSION_COL, row_idx), t_fg),
            ("FONTNAME",   (TENSION_COL, row_idx), (TENSION_COL, row_idx), "Helvetica-Bold"),
        ])

        # ΔV% Acum. > 8% → alerta
        if t.dv_acum_perc > 8.0:
            style_cmds.extend([
                ("TEXTCOLOR", (DV_ACUM_COL, row_idx), (DV_ACUM_COL, row_idx), RED_FAIL),
                ("FONTNAME",  (DV_ACUM_COL, row_idx), (DV_ACUM_COL, row_idx), "Helvetica-Bold"),
            ])

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    return elements


# ── Notas Técnicas de Rodapé ────────────────────────────────────────────────

def _build_footer_notes(styles: dict) -> list:
    elements: list = []
    elements.append(_hr())
    elements.append(Spacer(1, 1 * mm))

    notes = [
        "Icc calculado pelo método de Thévenin (impedância de sequência positiva). Valor exibido em kA.",
        "ΔV% Acumulado: limite regulatório de 8 % para rede BT conforme NTC 905200.",
        "Margem de crescimento de 15 % aplicada sobre a carga atual para projeção de demanda futura (NTC 905100).",
        "Temperatura do condutor calculada com T_ambiente = 30 °C. Limites: PVC ≤ 70 °C | XLPE/EPR ≤ 90 °C.",
        "Status 'Atenção' na coluna Tensão indica V_final fora da faixa nominal aceitável (< 91 % de V_nom).",
        f"Documento gerado automaticamente por CALC LIGHT em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
    ]
    for note in notes:
        elements.append(Paragraph(f"• {note}", styles["footer"]))

    return elements


# ── Função Principal ────────────────────────────────────────────────────────

def generate_memorial_pdf(
    project_name: str,
    created_at: str,
    trafo_nominal_kva: float,
    cqt_output: CqtOutputSchema,
) -> bytes:
    """
    Gera o Memorial de Cálculo Técnico em PDF.

    Args:
        project_name:      Nome do projeto (da tabela projects.name).
        created_at:        Data de criação do projeto (string ISO do SQLite).
        trafo_nominal_kva: Potência nominal do transformador em kVA.
        cqt_output:        Resultado completo do motor CQT (Fase 22).

    Returns:
        bytes do PDF, prontos para StreamingResponse com media_type='application/pdf'.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=f"Memorial de Cálculo — {project_name}",
        author="CALC LIGHT",
        subject="Queda de Tensão e Curto-Circuito — Rede BT",
    )

    styles = _build_styles()
    story: list = []

    # 1. Cabeçalho de identificação
    story.extend(_build_header_block(project_name, created_at, trafo_nominal_kva, styles))

    # 2. Resumo do transformador
    story.extend(_build_trafo_summary(cqt_output, trafo_nominal_kva, styles))

    # 3. Tabela de Trechos — Lado 1
    story.extend(_build_trecho_table(cqt_output.lado_1, "Lado 1", 2, styles))

    # 4. Tabela de Trechos — Lado 2 (pode estar vazia)
    story.extend(_build_trecho_table(cqt_output.lado_2, "Lado 2", 3, styles))

    # 5. Notas técnicas
    story.extend(_build_footer_notes(styles))

    doc.build(story)
    return buffer.getvalue()
