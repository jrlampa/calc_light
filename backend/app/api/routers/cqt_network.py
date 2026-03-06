"""
Rota de Cálculo de Rede Elétrica — Fase 22
POST /api/v1/calculate-network

Fluxo (Smart Backend):
  GraphPayloadSchema → TopologyParser.parse_to_cqt_input() → calcular_cqt_completo → CqtOutputSchema
"""
from fastapi import APIRouter, HTTPException

from app.domain.electrical_models import CqtOutputSchema, GraphPayloadSchema
from app.domain.electrical_services import LightElectricalService
from app.domain.topology_parser import TopologyError, TopologyParser

router_v1 = APIRouter(prefix="/api/v1", tags=["CQT Network"])

_parser = TopologyParser()
_service = LightElectricalService()


@router_v1.post("/calculate-network", response_model=CqtOutputSchema)
def calculate_network(payload: GraphPayloadSchema) -> CqtOutputSchema:
    """
    Recebe o grafo bruto do React Flow, valida a topologia (DAG anti-anel),
    ordena os nós e executa o motor elétrico completo:
      - Queda de Tensão (CQT%)
      - Corrente de Curto-Circuito (Icc)
      - Temperatura do Condutor
      - Carregamento do Transformador com Margem de Crescimento
    """
    try:
        cqt_input = _parser.parse_to_cqt_input(payload)
    except TopologyError as exc:
        raise HTTPException(status_code=422, detail=f"Topologia inválida: {exc}") from exc

    try:
        resultado: CqtOutputSchema = _service.calcular_cqt_completo(cqt_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no motor elétrico: {exc}") from exc

    return resultado
