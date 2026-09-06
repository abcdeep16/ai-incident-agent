import os
import time

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

from models.investigation import InvestigationResponse, EvidenceItem

# Gemini occasionally returns 503 "model is currently experiencing high
# demand" — this is transient overload on Google's side, not our bug.
# Retry a couple of times with a short backoff before giving up.
GEMINI_MAX_RETRIES = 2
GEMINI_RETRY_DELAY_SECONDS = 3

# Try these models in order. gemini-3.6-flash is the primary (currently
# the correct model for new API accounts). gemini-flash-latest is an
# alias Google keeps pointed at whatever their current stable Flash
# release is, used only as a fallback if 3.6-flash is still overloaded
# after all retries.
GEMINI_MODEL_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
]


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

    response = None
    last_error = None

    for model_name in GEMINI_MODEL_CANDIDATES:

        model_exhausted = False

        for attempt in range(1, GEMINI_MAX_RETRIES + 2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=InvestigationResponse,
                    ),
                )

                last_error = None
                break

            except Exception as error:

                last_error = error

                print("========================================")
                print(f"GEMINI ERROR (model={model_name}, attempt {attempt}):")
                print(repr(error))
                print("========================================")

                error_text = str(error)

                is_overloaded = (
                    "503" in error_text or "UNAVAILABLE" in error_text
                )
                is_model_unavailable = (
                    "404" in error_text or "NOT_FOUND" in error_text
                )
                is_quota_exhausted = (
                    "RESOURCE_EXHAUSTED" in error_text
                    or "429" in error_text
                )

                has_retries_left = attempt <= GEMINI_MAX_RETRIES

                if is_overloaded and has_retries_left:
                    print(
                        f"Gemini overloaded on {model_name}, retrying in "
                        f"{GEMINI_RETRY_DELAY_SECONDS}s "
                        f"(attempt {attempt}/{GEMINI_MAX_RETRIES})..."
                    )
                    time.sleep(GEMINI_RETRY_DELAY_SECONDS)
                    continue

                if is_overloaded or is_model_unavailable:
                    # Give up on this model, fall through to the next
                    # candidate model (if any).
                    model_exhausted = True
                    break

                if is_quota_exhausted:
                    # Project-level quota is shared across models, so
                    # trying another model won't help — fail immediately.
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            "Gemini API quota exceeded. "
                            "Please try again after the quota resets."
                        )
                    )

                # Unknown/non-retryable error — stop entirely.
                raise HTTPException(
                    status_code=502,
                    detail=f"AI service error: {str(error)}"
                )

        if last_error is None:
            # Success — stop trying further models.
            break

        if not model_exhausted:
            # Shouldn't normally get here, but guard against infinite loop.
            break

    if last_error is not None:

        # ----------------------------------------------
        # Gemini overloaded (still failing after retries)
        # ----------------------------------------------
        if "503" in str(last_error) or "UNAVAILABLE" in str(last_error):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini is temporarily unavailable due to high demand "
                    f"(tried {len(GEMINI_MODEL_CANDIDATES)} model(s), "
                    f"{GEMINI_MAX_RETRIES + 1} attempts each). "
                    "Please try again in a few moments."
                )
            )

        if (
            "RESOURCE_EXHAUSTED" in str(last_error)
            or "429" in str(last_error)
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
            detail=f"AI service error: {str(last_error)}"
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
