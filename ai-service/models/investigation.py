from pydantic import BaseModel


class InvestigationResponse(BaseModel):
    summary: str
    root_cause: str
    confidence: float
    evidence: list[str]
    next_steps: list[str]