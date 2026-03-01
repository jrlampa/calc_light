import json
import os
import re
import cmath
import math
from typing import List, Tuple, Dict
from .electrical_models import CqtInputSchema, CqtOutputSchema, TrechoResultSchema, RamalSchema, PosteSchema
from .exceptions import CableNotFoundError

class LightElectricalService:
    def __init__(self, catalog_path: str = None):
        if catalog_path is None:
            # Localização relativa ao arquivo electrical_services.py
            catalog_path = os.path.join(os.path.dirname(__file__), "data")
        self.catalog_path = catalog_path
        self.cables_list = self._load_json("cables_catalog_light.json")
        self.trafo_catalog = self._load_json("transformers_catalog_light.json")
        
        # Indexa cabos por nome para buscar R e X
        self.cables_dict = {str(c.get('conductor_name', '')): c for c in self.cables_list if isinstance(c, dict)}
        self.trafo_dict = {float(t.get('power_kva', 0)): t for t in self.trafo_catalog if isinstance(t, dict)}
        
        # Impedâncias de Referência (Ohm/km @ 20°C - Norma Light)
        self.z_ref_20c = {
            "240": 0.13138, "185": 0.22220, "70": 0.49065,
            "16": 1.15424, "107": 0.2968, "53": 0.6641, "33": 0.1162
        }

    def calcular_impedancia_trecho(self, condutor: str, comprimento_m: float) -> complex:
        """Busca R e X no catálogo e retorna Z = R + jX total do trecho (Lógica 21.9.4)"""
        tipo = str(condutor).upper()
        cable_data = self.cables_dict.get(tipo)
        
        # Fallback R_km Assumption (Norma 21.8) + X_km padrão (0.111 Ohm/km)
        if not cable_data:
            match = re.search(r"(\d+)", tipo)
            bitola = match.group(1) if match else "33"
            r_km = self.z_ref_20c.get(bitola, 0.1162)
            x_km = 0.111 
        else:
            r_km = cable_data.get('r_ohm_per_km', 0.1162)
            x_km = cable_data.get('x_ohm_per_km', 0.111)
            
        l_km = comprimento_m / 1000.0
        return complex(r_km * l_km, x_km * l_km)

    def _load_json(self, filename: str) -> List[dict]:
        path = os.path.join(self.catalog_path, filename)
        if not os.path.exists(path):
            # Fallback para diretório pai se não encontrado no catalog_path (Docker context)
            parent_path = os.path.join("..", filename)
            if os.path.exists(parent_path): path = parent_path
            
        if not os.path.exists(path):
            return []
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []

    def calcular_demanda_agregada(self, num_clientes: int) -> float:
        """Calcula demanda total diversificada em kVA (Lógica 21.3)"""
        if num_clientes < 0:
            raise ValueError("Número de clientes não pode ser negativo")
        if num_clientes == 0:
            return 0.0
            
        # Constantes da Light
        KVA_PER_CLIENT, N_MIN, N_MAX = 2.22, 4, 296
        FATOR_MIN, FATOR_MAX, STEP = 3.88, 83.00, 0.56
        
        if num_clientes <= N_MIN:
            fator_div = FATOR_MIN
        elif num_clientes >= N_MAX:
            fator_div = FATOR_MAX
        else:
            fator_div = FATOR_MIN + (num_clientes - N_MIN) * STEP
            
        return round(KVA_PER_CLIENT * fator_div, 4)

    def calcular_peso_poste(self, ramais: List[RamalSchema]) -> float:
        """Calcula o peso proporcional do poste baseado nos ramais (Lógica 21.3b)"""
        peso_total = 0.0
        amp_map = {
            "33 AA": 205, "53 AA": 272, "107 A": 418, "53 MX": 272,
            "70 MMX": 227, "185 MMX": 423, "33": 205, "53": 272,
            "107": 418, "16": 63, "240 CU": 430, "16 AL_CONC_TRI": 63
        }
        for r in ramais:
            tipo = r.tipo.upper()
            cable_data = self.cables_dict.get(tipo, {})
            ampacity = cable_data.get('ampacity_a', amp_map.get(tipo, 0))
            peso_total += r.qtd * ampacity
        return peso_total

    def calcular_temperatura_condutor(self, carga_kva: float, u_nominal: float, num_fases: int, condutor: str) -> Tuple[float, str]:
        """Calcula aquecimento do cabo e status térmico (Lógica 21.9.5)"""
        tipo = str(condutor).upper()
        cable_data = self.cables_dict.get(tipo, {})
        
        # Ampacidade baseada no catálogo ou fallback
        amp_map = {
            "33 AA": 205, "53 AA": 272, "107 A": 418, "53 MX": 272,
            "70 MMX": 227, "185 MMX": 423, "33": 205, "53": 272,
            "107": 418, "16": 63, "240 CU": 430, "16 AL_CONC_TRI": 63
        }
        ampacity = float(cable_data.get('ampacity_a', amp_map.get(tipo, 205)))
        
        # Conversão kVA -> Ampères
        if num_fases == 3:
            current = carga_kva / (u_nominal * math.sqrt(3.0) / 1000.0) if u_nominal > 0 else 0.0
        else:
            current = carga_kva / (u_nominal / 1000.0) if u_nominal > 0 else 0.0
            
        # Fórmula Light: T = 30 + (I / I_amp) * 60
        temp = 30.0 + (current / ampacity) * 60.0 if ampacity > 0 else 30.0
        
        # Limite PVC vs XLPE (PVC = 70C, XLPE/EPR = 90C)
        pvc_cables = ["13 AL", "21 AL", "53 AL", "13 AL - DX", "13 AL - TX", "13 AL - QX", "21 AL - QX", "53 AL - QX"]
        limit = 70.1 if any(pvc in tipo for pvc in pvc_cables) else 90.1
        
        status = "Ok !" if temp <= limit else f"Reprovado! (> {limit-0.1:.0f}°C)"
        return round(temp, 2), status

    def ratear_carga_trafo(self, leitura_trafo: float, pesos_l1: List[float], pesos_l2: List[float]) -> Tuple[List[float], List[float]]:
        """Distribui a carga do trafo entre todos os postes (Lógica 21.4)"""
        demanda_corrigida = leitura_trafo * 0.375
        w_total = sum(pesos_l1) + sum(pesos_l2)
        
        if w_total == 0:
            return [0.0] * len(pesos_l1), [0.0] * len(pesos_l2)
            
        cargas_l1 = [(demanda_corrigida * w / w_total) for w in pesos_l1]
        cargas_l2 = [(demanda_corrigida * w / w_total) for w in pesos_l2]
        return cargas_l1, cargas_l2

    def calcular_cqt_trecho(self, carga_acum: float, condutor: str, comprimento: float, num_fases: int, tipo_trecho: str = "rede") -> float:
        """Calcula dV% baseado na física fundamental (Norma 21.8)"""
        match = re.search(r"(\d+)", str(condutor))
        bitola = match.group(1) if match else None
        
        if (not bitola or bitola not in self.z_ref_20c) and str(condutor).upper() not in self.cables_dict:
            raise CableNotFoundError(f"Condutor '{condutor}' não encontrado.")
            
        z_equiv = self.z_ref_20c.get(bitola, 0.1162)
        v_base = 220.0 
        
        if tipo_trecho.lower() in ["rl", "ramal"]:
            fase_map = {3: 2.0, 2: 2.0, 1: 6.0}
        else:
            fase_map = {3: 1.0, 2: 2.0, 1: 6.0}
            
        f_fase = fase_map.get(num_fases, 1.0)
        dv_perc = (carga_acum * z_equiv * comprimento) / ((v_base ** 2) / 100.0)
        
        return dv_perc * f_fase

    def calcular_cqt_completo(self, data: CqtInputSchema) -> CqtOutputSchema:
        """Processa o cálculo completo da rede com sanitização Pydantic (Lógica Versão Ouro)"""
        pesos_l1 = [self.calcular_peso_poste(p.ramais) for p in data.lado_1]
        pesos_l2 = [self.calcular_peso_poste(p.ramais) for p in data.lado_2]
        
        cargas_l1, cargas_l2 = self.ratear_carga_trafo(data.leitura_trafo, pesos_l1, pesos_l2)
        
        # Busca Queda Inicial (Trafo)
        trafo_data = self.trafo_dict.get(float(data.trafo_nominal_kva), {})
        if not trafo_data:
            powers = sorted(self.trafo_dict.keys())
            if powers:
                best_p = min(powers, key=lambda x: abs(x - data.trafo_nominal_kva))
                trafo_data = self.trafo_dict[best_p]
        
        dv_prim = float(trafo_data.get("dv_primary_pct", 0.43))
        dv_trafo = float(trafo_data.get("dv_transformer_pct", 4.5))
        
        # Impedância do Trafo (Z = R + jX)
        # |Z| = (dV_trafo / 100) * (V^2 / S_nom)
        v_base_pp = 220.0
        s_nom_va = data.trafo_nominal_kva * 1000.0
        z_mod_trafo = (dv_trafo / 100.0) * (v_base_pp**2 / s_nom_va)
        
        # Decomposição R + jX com X/R = 3.0 -> R = |Z| / sqrt(1+3^2)
        r_trafo = z_mod_trafo / math.sqrt(10.0)
        x_trafo = 3.0 * r_trafo
        z_trafo_complex = complex(r_trafo, x_trafo)
        
        resultados = {"lado_1": [], "lado_2": []}
        
        for side_name, side_cargas, side_pts in [("lado_1", cargas_l1, data.lado_1), ("lado_2", cargas_l2, data.lado_2)]:
            dv_acum = (dv_prim + dv_trafo) if data.leitura_trafo > 0 else 0.0
            z_acum = z_trafo_complex if data.leitura_trafo > 0 else complex(1e-9, 1e-9) # Impedância mínima para não dar ZeroDivision
            
            for i, p in enumerate(side_pts):
                carga_no_trecho = sum(side_cargas[i:])
                tipo = "rl" if "RAMAL" in p.id.upper() or p.tipo_trecho == "rl" else "rede"
                
                dv_trecho = self.calcular_cqt_trecho(carga_no_trecho, p.condutor, p.comprimento, p.fases, tipo)
                dv_acum += dv_trecho
                v_final = max(0.0, data.u_nominal * (1 - dv_acum / 100))
                
                # Cálculo Icc (Trifásico Simétrico)
                z_trecho = self.calcular_impedancia_trecho(p.condutor, p.comprimento)
                z_acum += z_trecho
                # Icc = U_fase / |Z_acum|
                icc = data.u_nominal / abs(z_acum) if abs(z_acum) > 0 else 0.0
                
                # Cálculo Térmico
                temp_c, t_status = self.calcular_temperatura_condutor(carga_no_trecho, data.u_nominal, p.fases, p.condutor)
                
                limite = 202 if data.u_nominal >= 220 else 117
                status = "Ok" if v_final >= limite else "Cuidado! Tensão Baixa"
                
                resultados[side_name].append(TrechoResultSchema(
                    id=p.id,
                    carga_kva=round(side_cargas[i], 3),
                    carga_acum_kva=round(carga_no_trecho, 3),
                    dv_trecho_perc=round(dv_trecho, 4),
                    dv_acum_perc=round(dv_acum, 4),
                    v_final=round(v_final, 2),
                    icc_amperes=round(icc, 2),
                    cable_temp_celsius=temp_c,
                    thermal_status=t_status,
                    status=status
                ))
        # Cálculo do Carregamento do Trafo (Lógica 21.9.6)
        # carga_atual = total de kVA distribuído + correção de rateio
        carga_atual_kva = (data.leitura_trafo * 0.375)
        
        # Projeção correta: Carga_Projetada = Carga_Atual / (1 - Margem)
        # Garante que a carga_atual ocupe exatamente (1 - margem) da capacidade total
        margem = data.growth_margin_pct
        carga_projetada_kva = carga_atual_kva / (1.0 - margem) if margem < 1.0 else float('inf')
        
        trafo_loading_pct = (carga_projetada_kva / data.trafo_nominal_kva) * 100.0
        trafo_status = "Ok" if trafo_loading_pct <= 100.0 else "Sobrecarga"
        
        return CqtOutputSchema(
            **resultados,
            carga_atual_kva=round(carga_atual_kva, 3),
            carga_projetada_kva=round(carga_projetada_kva, 3),
            trafo_loading_percent=round(trafo_loading_pct, 2),
            trafo_status=trafo_status
        )
