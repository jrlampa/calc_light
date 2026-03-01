from pydantic import BaseModel


class ParsedPointResponse(BaseModel):
    """Ponto geoespacial retornado pelo endpoint parse-file."""

    label: str
    lat: float
    lng: float


class ImportPointRequest(BaseModel):
    """Ponto selecionado pelo usuário para importação."""

    label: str
    lat: float
    lng: float


class ImportNodesRequest(BaseModel):
    """Payload do endpoint import-nodes."""

    points: list[ImportPointRequest]


class OutgoingConductorsResponse(BaseModel):
    """Condutores do vão de saída de um nó (Herança de Condutores)."""

    mt_conductor_id: int | None = None
    mt_sag_m: float = 0.0
    bt_conductor_id: int | None = None
    bt_sag_m: float = 0.0
