import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.investigation import InvestigationResponse
from retrieval.retriever import retrieve_evidence
from services.llm_service import generate_response

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_ORIGINS = [
    origin.strip() for origin in FRONTEND_URL.split(",") if origin.strip()
]
for dev_origin in ("http://localhost:5173", "http://localhost:5174"):
    if dev_origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(dev_origin)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str
    service: str


@app.get("/health")
@app.head("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-service",
        "model": "local-log-anomaly-model",
    }


@app.post("/generate", response_model=InvestigationResponse)
def generate(request: GenerateRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Incident prompt cannot be empty.")
    if not request.service.strip():
        raise HTTPException(status_code=400, detail="Service name cannot be empty.")

    try:
        evidence = retrieve_evidence(request.service, request.prompt)
    except Exception as error:
        print("========================================")
        print("RETRIEVAL ERROR:")
        print(repr(error))
        print("========================================")
        raise HTTPException(
            status_code=500,
            detail=f"Evidence retrieval failed: {str(error)}",
        )

    try:
        return generate_response(request.prompt, evidence)
    except HTTPException:
        raise
    except Exception as error:
        print("========================================")
        print("MODEL GENERATION ERROR:")
        print(repr(error))
        print("========================================")
        raise HTTPException(
            status_code=502,
            detail=f"Local model inference failed: {str(error)}",
        )