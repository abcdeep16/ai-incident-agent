from models.investigation import InvestigationResponse, EvidenceItem
from services.local_model_service import predict_text


def calculate_evidence_confidence(evidence: list[str]) -> float:
    if not evidence:
        return 0.0

    scores = []
    for item in evidence:
        if "[SIMILARITY:" not in item:
            continue
        try:
            score_text = item.split("[SIMILARITY:")[1].split("]")[0]
            scores.append(float(score_text))
        except (ValueError, IndexError):
            continue

    if not scores:
        return 0.0
    return round(min(1.0, sum(scores) / len(scores)), 4)


def generate_response(prompt: str, evidence: list[str]) -> InvestigationResponse:
    model_result = predict_text(prompt)
    anomaly_probability = float(model_result["anomaly_probability"])
    confidence = float(model_result["confidence"])
    prediction = model_result["prediction"]

    if not evidence:
        evidence = [f"[MODEL] {prompt}"]

    structured_evidence = []
    for item in evidence[:5]:
        source = "MODEL"
        similarity = max(0.0, min(1.0, anomaly_probability))
        content = item
        if item.startswith("[SIMILARITY:"):
            try:
                similarity = float(item.split("[SIMILARITY:")[1].split("]")[0])
                content = item.split("]", 1)[1].strip() if "]" in item else item.strip()
            except (ValueError, IndexError):
                pass
        if content.startswith("[LOG]"):
            content = content[len("[LOG]"):].strip()
        elif content.startswith("[METRIC]"):
            content = content[len("[METRIC]"):].strip()
        elif content.startswith("[DEPLOYMENT]"):
            content = content[len("[DEPLOYMENT]"):].strip()
        structured_evidence.append(
            EvidenceItem(
                source=source,
                similarity=round(similarity, 4),
                content=content,
            )
        )

    if prediction == "anomaly":
        summary = (
            "The local anomaly model detected a likely operational fault pattern in the supplied incident text."
        )
        root_cause = (
            "The request resembles known fault signatures in the training corpus, including failure-oriented log phrases and error conditions."
        )
        next_steps = [
            "Inspect recent service logs and infrastructure status pages.",
            "Check for server, network, or dependency failures around the event time.",
            "Validate recent configuration or deployment changes before rollout."
        ]
    else:
        summary = "The local model did not identify a strong anomaly signal in the supplied text."
        root_cause = "No strong failure signature was detected; the issue may be environmental, intermittent, or outside the current training scope."
        next_steps = [
            "Gather additional logs and timestamps for the incident.",
            "Compare environment metrics with adjacent intervals.",
            "Review service dependencies and recent configuration drift."
        ]

    return InvestigationResponse(
        summary=summary,
        root_cause=root_cause,
        confidence=round(max(confidence, calculate_evidence_confidence([item for item in evidence if item])), 4),
        evidence=structured_evidence,
        next_steps=next_steps,
    )
