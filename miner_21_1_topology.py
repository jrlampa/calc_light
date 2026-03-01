import openpyxl
from openpyxl import load_workbook
import os

def miner_21_1_topology():
    filename = "PLANILHA_DESTRAVADA.xlsm"
    report_name = "21_1_TOPOLOGY_REPORT.txt"
    
    if not os.path.exists(filename):
        print(f"Erro: Arquivo {filename} não encontrado.")
        return

    print(f"Carregando {filename} (isso pode demorar devido ao tamanho e macros)...")
    # data_only=False para podermos ver as fórmulas se necessário no futuro, 
    # mas para nomes definidos e estrutura o padrão serve.
    # keep_vba=True porque é um .xlsm
    wb = load_workbook(filename, keep_vba=True, data_only=True)
    
    report_lines = []
    report_lines.append("="*60)
    report_lines.append("RELATÓRIO DE TOPOGRAFIA DA PLANILHA - FASE 21.1")
    report_lines.append("="*60)
    report_lines.append("")

    # 1. Mapeamento de Abas
    report_lines.append("[1] MAPEAMENTO DE ABAS (SHEETS)")
    report_lines.append("-" * 30)
    for sheet in wb.worksheets:
        state = sheet.sheet_state # 'visible', 'hidden', or 'veryHidden'
        report_lines.append(f"Aba: {sheet.title:.<40} Estado: {state}")
    report_lines.append("")

    # 2. Extração de Named Ranges (Defined Names)
    report_lines.append("[2] DICIONÁRIO DE DEFINED NAMES (NAMED RANGES)")
    report_lines.append("-" * 30)
    
    # wb.defined_names em versões recentes de openpyxl contém um dicionário-like
    if not wb.defined_names:
        report_lines.append("Nenhum Named Range encontrado.")
    else:
        for name, defn in wb.defined_names.items():
            # defn.value contém a referência (ex: 'Planilha1!$A$1')
            report_lines.append(f"Nome: {name:.<40} Ref: {defn.value}")
    report_lines.append("")

    # 3. Varredura Heurística de Catálogos
    report_lines.append("[3] VARREDURA HEURÍSTICA DE CATÁLOGOS")
    report_lines.append("-" * 30)
    keywords = ["Cabo", "AWG", "MCM", "Resistência", "Ohms", "Reatância", "Ampacidade", "kVA", "Transformador"]
    
    found_catalogs = []
    
    for sheet in wb.worksheets:
        # Varredura limitada para evitar overhead excessivo em planilhas gigantes
        # Procuramos nos primeiros 200 linhas e 50 colunas (onde geralmente ficam os cabeçalhos)
        max_search_row = min(sheet.max_row, 300)
        max_search_col = min(sheet.max_column, 50)
        
        for row in range(1, max_search_row + 1):
            for col in range(1, max_search_col + 1):
                cell_value = sheet.cell(row=row, column=col).value
                if cell_value and any(kw.lower() in str(cell_value).lower() for kw in keywords):
                    found_catalogs.append(f"Possível Cabeçalho: '{cell_value}' em {sheet.title}!{sheet.cell(row=row, column=col).coordinate}")
                    # Uma vez que achamos um candidato, podemos registrar o bloco ao redor (ex: A1:E20)
                    # mas para este script exploratório, apenas a coordenada do 'hit' já ajuda muito.

    if not found_catalogs:
        report_lines.append("Nenhum cabeçalho de catálogo identificado por heurística.")
    else:
        for item in found_catalogs:
            report_lines.append(item)
    report_lines.append("")

    # Escrita do Relatório
    with open(report_name, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Relatório gerado com sucesso: {report_name}")

if __name__ == "__main__":
    miner_21_1_topology()
