from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class RamalSchema(BaseModel):
    tipo: str = Field(..., description="Tipo de condutor do ramal")
    qtd: int = Field(..., ge=0, description="Quantidade de ramais")

    @field_validator('tipo')
    def clean_tipo(cls, v):
        return v.strip().upper()

class PosteSchema(BaseModel):
    id: str = Field(..., description="Identificador do poste")
    condutor: str = Field(..., description="Condutor principal do trecho")
    comprimento: float = Field(..., ge=0, description="Comprimento do trecho em metros")
    fases: int = Field(..., ge=1, le=3, description="Número de fases")
    ramais: List[RamalSchema] = Field(default_factory=list)
    tipo_trecho: Optional[str] = Field("rede", description="Tipo do trecho: rede ou rl (ramal)")

    @field_validator('condutor', 'id')
    def clean_strings(cls, v):
        return v.strip()

class CqtInputSchema(BaseModel):
    u_nominal: float = Field(127.0, gt=0, description="Tensão nominal de fase (LN)")
    leitura_trafo: float = Field(0.0, ge=0, description="Leitura de corrente ou kVA no trafo")
    trafo_nominal_kva: float = Field(112.5, gt=0, description="Potência nominal do transformador")
    growth_margin_pct: float = Field(0.15, ge=0, lt=1, description="Margem de crescimento (ex: 0.15 = 15%)")
    lado_1: List[PosteSchema] = Field(default_factory=list)
    lado_2: List[PosteSchema] = Field(default_factory=list)

class TrechoResultSchema(BaseModel):
    id: str
    carga_kva: float
    carga_acum_kva: float
    dv_trecho_perc: float
    dv_acum_perc: float
    v_final: float
    icc_amperes: float
    cable_temp_celsius: float
    thermal_status: str
    status: str

class CqtOutputSchema(BaseModel):
    lado_1: List[TrechoResultSchema]
    lado_2: List[TrechoResultSchema]
    carga_atual_kva: float
    carga_projetada_kva: float
    trafo_loading_percent: float
    trafo_status: str

# --- Schemas para o Tradutor Topológico (Fase 21.9.3) ---

class GraphNodeSchema(BaseModel):
    id: str
    label: str = ""
    is_transformer: bool = False
    ramais: List[RamalSchema] = Field(default_factory=list)

class GraphEdgeSchema(BaseModel):
    id: str
    source: str  # ID do nó de origem
    target: str  # ID do nó de destino
    condutor: str
    comprimento: float = Field(..., ge=0)
    fases: int = Field(..., ge=1, le=3)
    tipo_trecho: Optional[str] = "rede"

class GraphPayloadSchema(BaseModel):
    u_nominal: float = Field(127.0, gt=0)
    leitura_trafo: float = Field(0.0, ge=0)
    trafo_nominal_kva: float = Field(112.5, gt=0)
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]
