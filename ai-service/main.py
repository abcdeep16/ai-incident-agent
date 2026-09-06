import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.investigation import InvestigationResponse
from services.llm_service import generate_response
from retrieval.retriever import retrieve_evidence

load_dotenv()

# Comma-separated list of allowed frontend origins.
# Example: FRONTEND_URL=https://ai-incident-frontend.onrender.com
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in FRONTEND_URL.split(",")
    if origin.strip()
]

# Always allow common local dev ports too.
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
        "service": "ai-service"
    }


@app.post("/generate", response_model=InvestigationResponse)
def generate(request: GenerateRequest):

    # ---------------------------------------------
    # 1. Validate request
    # ---------------------------------------------

    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Incident prompt cannot be empty."
        )

    if not request.service.strip():
        raise HTTPException(
            status_code=400,
            detail="Service name cannot be empty."
        )

    # ---------------------------------------------
    # 2. Retrieve evidence
    # ---------------------------------------------

    try:
        evidence = retrieve_evidence(
            request.service,
            request.prompt
        )

    except Exception as error:

        print("========================================")
        print("RETRIEVAL ERROR:")
        print(repr(error))
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=f"Evidence retrieval failed: {str(error)}"
        )

    # ---------------------------------------------
    # 3. Handle no relevant evidence
    # ---------------------------------------------

    if not evidence:
        return {
            "summary": "Insufficient relevant evidence was found.",
            "root_cause": "Unknown",
            "confidence": 0.0,
            "evidence": [],
            "next_steps": [
                "Collect relevant application logs.",
                "Check service metrics around the incident time.",
                "Review recent deployments or configuration changes."
            ]
        }

    # ---------------------------------------------
    # 4. Generate AI investigation
    # ---------------------------------------------

    try:

        return generate_response(
            request.prompt,
            evidence
        )

    except HTTPException:
        # Preserve errors such as Gemini 429/502/503
        raise

    except Exception as error:

        print("========================================")
        print("AI GENERATION ERROR:")
        print(repr(error))
        print("========================================")

        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(error)}"
        )