from pydantic import BaseModel


class EvidenceItem(BaseModel):

    source: str

    similarity: float

    content: str


class InvestigationResponse(BaseModel):

    summary: str

    root_cause: str

    confidence: float

    evidence: list[EvidenceItem]

    next_steps: list[str]
