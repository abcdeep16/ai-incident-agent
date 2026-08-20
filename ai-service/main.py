from fastapi import FastAPI
from pydantic import BaseModel

from models.investigation import InvestigationResponse
from services.llm_service import generate_response


app = FastAPI()


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-service"
    }


@app.post("/generate", response_model=InvestigationResponse)
def generate(request: GenerateRequest):
    return generate_response(request.prompt)