"""
light_cqt_core.py
Fase 21.7 - CACL LIGHT
Motor de Cálculo de Queda de Tensão (CQT) Puro e Isolado.
Consolida as regras de negócio extraídas da PLANILHA_DESTRAVADA.xlsm.
"""

import json
import math
import os
import re

class CableNotFoundError(Exception):
    """Lançado quando um condutor não é encontrado no catálogo."""
    pass

class LightElectricalEngine:
    def __init__(self, catalog_path="."):
        self.catalog_path = catalog_path
        # Carrega como listas
        self.cables_list = self._load_json("cables_catalog_light.json")
        self.vdrop_list = self._load_json("voltage_drop_coef_light.json")
        self.demand_curve = self._load_json("demand_curve_light.json")
        
        # Indexa cabos por nome para buscar R e X
        self.cables_dict = {str(c.get('conductor_name', '')): c for c in self.cables_list if isinstance(c, dict)}
        
        # Impedâncias de Referência (Ohm/km @ 20°C - Norma Light)
        # Extraídas da auditoria técnica da PLANILHA_DESTRAVADA.xlsm
        self.z_ref_20c = {
            "240": 0.13138,  # 240 Cu
            "185": 0.22220,  # 185 Al
            "70": 0.49065,   # 70 Al
            "16": 1.15424,   # 16 Al
            "107": 0.2968,   # 107
            "53": 0.6641,    # 53 MX
            "33": 0.1162     # 33 AA (Base)
        }

        # Indexa coeficientes de trafo por kVA
        self.trafo_catalog = self._load_json("transformers_catalog_light.json")
        self.trafo_dict = {float(t.get('power_kva', 0)): t for t in self.trafo_catalog if isinstance(t, dict)}
        
    def _load_json(self, filename):
        path = os.path.join(self.catalog_path, filename)
        if not os.path.exists(path):
            print(f"Aviso: {filename} não encontrado em {self.catalog_path}")
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []

    def calcular_demanda_agregada(self, num_clientes, tipo="normal"):
        if num_clientes < 0:
            raise ValueError("Número de clientes não pode ser negativo")
        if num_clientes == 0:
            return 0.0
        KVA_PER_CLIENT = 2.22
        N_MIN = 4
        N_MAX = 296
        FATOR_MIN = 3.88
        FATOR_MAX = 83.00
        STEP = 0.56
        if num_clientes <= N_MIN:
            fator_div = FATOR_MIN
        elif num_clientes >= N_MAX:
            fator_div = FATOR_MAX
        else:
            fator_div = FATOR_MIN + (num_clientes - N_MIN) * STEP
        return round(KVA_PER_CLIENT * fator_div, 4)

    def calcular_peso_poste(self, ramais):
        peso_total = 0.0
        for r in ramais:
            tipo = str(r.get('tipo', ''))
            qtd = r.get('qtd', 0)
            cable_data = self.cables_dict.get(tipo, {})
            ampacity = cable_data.get('ampacity_a', 0)
            if ampacity == 0:
                # Fallback manual para nomes de condutores 
                amp_map = {
                    "33 AA": 205, "53 AA": 272, "107 A": 418,
                    "53 MX": 272, "70 MMX": 227, "185 MMX": 423,
                    "33": 205, "53": 272, "107": 418, "16": 63,
                    "240 Cu": 500, "16 Al_CONC_Tri": 63
                }
                ampacity = amp_map.get(tipo, 0)
            peso_total += qtd * ampacity
        return peso_total

    def ratear_carga_trafo(self, leitura_trafo, pesos_lado_1, pesos_lado_2):
        demanda_corrigida = leitura_trafo * 0.375 # Fator G9 (0.375 * G3)
        w_total = sum(pesos_lado_1) + sum(pesos_lado_2)
        if w_total == 0: return [0]*len(pesos_lado_1), [0]*len(pesos_lado_2)
        cargas_l1 = [(demanda_corrigida * w / w_total) for w in pesos_lado_1]
        cargas_l2 = [(demanda_corrigida * w / w_total) for w in pesos_lado_2]
        return cargas_l1, cargas_l2

    def calcular_cqt_trecho(self, carga_acum, condutor, comprimento, num_fases, tipo_trecho="rede"):
        """
        Calcula dV% baseado na física fundamental e regras de negócio da Light.
        Fórmula: dV% = (S * Z * L) / (V_base^2 / 100) * F_fase
        """
        # 1. Recuperar Impedância (Z em Ohm/km @ 20°C)
        # Tenta match pela bitola (especificação técnica da Light)
        match = re.search(r"(\d+)", str(condutor))
        bitola = match.group(1) if match else None
        
        if (not bitola or bitola not in self.z_ref_20c) and str(condutor) not in self.cables_dict:
            raise CableNotFoundError(f"Condutor '{condutor}' não encontrado no catálogo.")
            
        z_equiv = self.z_ref_20c.get(bitola, 0.1162)
        
        # 2. Constantes de Tensão (Base BT Light: 220V LL)
        v_base = 220.0 
        
        # 3. Fator de Fase / Desequilíbrio (Ref: BZ14 e BZ20 da Planilha)
        # Rede (rede): 3f=1.0, 2f=2.0, 1f=6.0
        # Ramal (rl):   3f=2.0, 2f=2.0, 1f=6.0 (Regra específica para Ramais de Ligação)
        if str(tipo_trecho).lower() in ["rl", "ramal"]:
            fase_map = {3: 2.0, 2: 2.0, 1: 6.0}
        else:
            fase_map = {3: 1.0, 2: 2.0, 1: 6.0}
            
        f_fase = fase_map.get(num_fases, 1.0)
        
        # 4. Cálculo dV% (L em metros, Z em ohm/km)
        divisor_base = (v_base ** 2) / 100.0
        dv_perc = (carga_acum * z_equiv * comprimento) / divisor_base
        
        return dv_perc * f_fase

    def processar_calculo_rede(self, payload):
        u_nom = payload.get("u_nominal", 127)
        leitura_trafo = payload.get("leitura_trafo", 0)
        pesos_l1 = [self.calcular_peso_poste(p.get("ramais", [])) for p in payload.get("lado_1", [])]
        pesos_l2 = [self.calcular_peso_poste(p.get("ramais", [])) for p in payload.get("lado_2", [])]
        cargas_l1, cargas_l2 = self.ratear_carga_trafo(leitura_trafo, pesos_l1, pesos_l2)
        resultados = {"lado_1": [], "lado_2": []}
        
        # 1. Queda Inicial (Primária + Trafo)
        pot_nominal = payload.get("trafo_nominal_kva", 112.5)
        trafo_data = self.trafo_dict.get(float(pot_nominal), {})
        if not trafo_data:
            powers = sorted(self.trafo_dict.keys())
            if powers:
                best_p = min(powers, key=lambda x: abs(x - pot_nominal))
                trafo_data = self.trafo_dict[best_p]
        
        dv_prim = float(trafo_data.get("dv_primary_pct", 0.43))
        dv_trafo = float(trafo_data.get("dv_transformer_pct", 4.5))
        
        for lado, cargas, pts in [("lado_1", cargas_l1, payload.get("lado_1", [])), 
                                 ("lado_2", cargas_l2, payload.get("lado_2", []))]:
            # Iniciamos com a queda acumulada até a saída do Trafo
            # Se leitura_trafo é zero, a queda inicial também é zero
            dv_acum = (dv_prim + dv_trafo) if leitura_trafo > 0 else 0.0
            
            for i in range(len(pts)):
                carga_no_trecho = sum(cargas[i:])
                p = pts[i]
                tipo = p.get("tipo_trecho", "rede")
                # Se o ID contém 'RAMAL', força tipo 'rl' para disparar regra de fase 2.0
                if "RAMAL" in str(p.get("id", "")).upper(): tipo = "rl"
                
                dv_trecho = self.calcular_cqt_trecho(carga_no_trecho, p["condutor"], p["comprimento"], p["fases"], tipo)
                dv_acum += dv_trecho
                v_linha = u_nom * (1 - dv_acum / 100)
                # Clamping físico (Tensão não pode ser negativa por queda ohmica)
                v_linha = max(0.0, v_linha)
                
                status = "Ok"
                limite = 202 if u_nom >= 220 else 117
                if v_linha < limite: status = "Cuidado! Tensão Baixa"
                resultados[lado].append({
                    "id": p["id"],
                    "carga_kva": round(cargas[i], 3),
                    "carga_acum_kva": round(carga_no_trecho, 3),
                    "dv_trecho_perc": round(dv_trecho, 4),
                    "dv_acum_perc": round(dv_acum, 4),
                    "v_final": round(v_linha, 2),
                    "status": status
                })
        return resultados
