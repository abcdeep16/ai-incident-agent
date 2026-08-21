import os

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

from models.investigation import InvestigationResponse, EvidenceItem


# ==================================================
# Environment / Gemini Client
# ==================================================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==================================================
# System Prompt
# ==================================================

SYSTEM_PROMPT = """
You are an AI software engineering assistant.

Your job is to analyze software engineering problems
carefully and provide practical, evidence-based answers.

Rules:
1. Do not invent logs, metrics, files, or facts.
2. Clearly distinguish evidence from assumptions.
3. If the available information is insufficient, say so.
4. Keep responses concise and technically useful.
5. Return your answer using the requested structured format.
"""


# ==================================================
# Evidence Confidence
# ==================================================

def calculate_evidence_confidence(
    evidence: list[str]
) -> float:

    if not evidence:
        return 0.0

    scores = []
    diagnostic_count = 0

    diagnostic_keywords = [
        "error",
        "failed",
        "failure",
        "exception",
        "500",
        "timeout",
        "timed out",
        "connection failed",
        "connection refused",
        "database",
        "unavailable",
        "crash",
        "critical",
        "warn",
        "warning",
    ]

    for item in evidence:

        # ---------------------------------------------
        # Extract semantic similarity
        # ---------------------------------------------

        if "[SIMILARITY:" not in item:
            continue

        try:

            score_text = (
                item.split("[SIMILARITY:")[1]
                .split("]")[0]
            )

            score = float(score_text)

            scores.append(score)

        except (ValueError, IndexError):
            continue

        # ---------------------------------------------
        # Check diagnostic evidence
        # ---------------------------------------------

        text = item.lower()

        if any(
            keyword in text
            for keyword in diagnostic_keywords
        ):
            diagnostic_count += 1

    # ---------------------------------------------
    # No valid similarity scores
    # ---------------------------------------------

    if not scores:
        return 0.0

    # ---------------------------------------------
    # Base confidence
    # ---------------------------------------------

    average_score = sum(scores) / len(scores)

    # ---------------------------------------------
    # Evidence coverage bonus
    # ---------------------------------------------

    evidence_bonus = min(
        len(scores) * 0.05,
        0.20
    )

    # ---------------------------------------------
    # Diagnostic evidence bonus
    # ---------------------------------------------

    diagnostic_bonus = min(
        diagnostic_count * 0.05,
        0.20
    )

    # ---------------------------------------------
    # Final confidence
    # ---------------------------------------------

    confidence = (
        average_score
        + evidence_bonus
        + diagnostic_bonus
    )

    return round(
        max(0.0, min(1.0, confidence)),
        2
    )


# ==================================================
# Generate Investigation Response
# ==================================================

def generate_response(
    prompt: str,
    evidence: list[str]
) -> InvestigationResponse:

    # ==================================================
    # 1. Evidence Guard
    # ==================================================

    if not evidence:

        return InvestigationResponse(
            summary="Insufficient relevant evidence was found.",

            root_cause="Unknown",

            confidence=0.0,

            evidence=[],

            next_steps=[
                "Collect relevant application logs.",
                "Check service metrics around the incident time.",
                "Review recent deployments or configuration changes."
            ]
        )

    # ==================================================
    # 2. Calculate Evidence Confidence
    # ==================================================

    evidence_confidence = calculate_evidence_confidence(
        evidence
    )

    # ==================================================
    # 3. Prepare Evidence for Gemini
    # ==================================================

    evidence_text = "\n".join(
        f"- {item}"
        for item in evidence
    )

    # ==================================================
    # 4. Build Gemini Prompt
    # ==================================================

    full_prompt = f"""
Incident:
{prompt}

Relevant engineering evidence:
{evidence_text}

Evidence retrieval confidence:
{evidence_confidence}

Each evidence item may contain:
- a source type such as [LOG], [METRIC], or [DEPLOYMENT]
- a semantic similarity score
- the actual evidence content

Use the provided evidence to analyze the incident.

Important rules:
- Base conclusions on the provided evidence.
- Do not invent logs, metrics, deployments, or other facts.
- Treat similarity scores as relevance signals, not proof.
- Distinguish confirmed evidence from possible explanations.
- If the evidence is insufficient, clearly say so.
"""


    # ==================================================
    # 5. Call Gemini
    # ==================================================

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=InvestigationResponse,
            ),
        )

    except Exception as error:

        print("========================================")
        print("GEMINI ERROR:")
        print(repr(error))
        print("========================================")

        # ----------------------------------------------
        # Gemini quota / rate limit
        # ----------------------------------------------
        if "503" in str(error) or "UNAVAILABLE" in str(error):
            raise HTTPException(
        status_code=503,
        detail=(
            "Gemini is temporarily unavailable due to high demand. "
            "Please try again in a few moments."
        )
    )

        if (
             "RESOURCE_EXHAUSTED" in str(error)
            or "429" in str(error)
):
            raise HTTPException(
        status_code=429,
        detail=(
            "Gemini API quota exceeded. "
            "Please try again after the quota resets."
        )
    )
            

        # ----------------------------------------------
        # Other Gemini errors
        # ----------------------------------------------

        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(error)}"
        )

    # ==================================================
    # 6. Parse Gemini Response
    # ==================================================

    result = InvestigationResponse.model_validate_json(
        response.text
    )

    # ==================================================
    # 7. Use Backend-calculated Confidence
    # ==================================================

    result.confidence = evidence_confidence

    # ==================================================
    # 8. Convert Evidence to Structured EvidenceItems
    # ==================================================

    structured_evidence = []

    for item in evidence:

        try:

            # ------------------------------------------
            # Extract similarity
            # ------------------------------------------

            similarity = float(
                item
                .split("[SIMILARITY:")[1]
                .split("]")[0]
            )

            # ------------------------------------------
            # Detect source
            # ------------------------------------------

            source = "UNKNOWN"

            if "[LOG]" in item:
                source = "LOG"

            elif "[METRIC]" in item:
                source = "METRIC"

            elif "[DEPLOYMENT]" in item:
                source = "DEPLOYMENT"

            # ------------------------------------------
            # Extract content
            # ------------------------------------------

            content = item

            if "[SIMILARITY:" in content:
                content = content.split("]", 1)[1].strip()

            if content.startswith("[LOG]"):
                content = content[len("[LOG]"):].strip()

            elif content.startswith("[METRIC]"):
                content = content[len("[METRIC]"):].strip()

            elif content.startswith("[DEPLOYMENT]"):
                content = content[len("[DEPLOYMENT]"):].strip()
            # ------------------------------------------
            # Create structured evidence
            # ------------------------------------------

            structured_evidence.append(
                EvidenceItem(
                    source=source,
                    similarity=similarity,
                    content=content
                )
            )

        except (ValueError, IndexError):

            continue

    # ==================================================
    # 9. Attach Structured Evidence
    # ==================================================

    result.evidence = structured_evidence

    # ==================================================
    # 10. Return Final Investigation
    # ==================================================

    return result