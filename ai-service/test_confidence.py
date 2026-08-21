from services.llm_service import calculate_evidence_confidence


evidence = [
    "[SIMILARITY: 0.729]\n[LOG]\nHTTP 500 returned",
    "[SIMILARITY: 0.680]\n[LOG]\nDatabase connection failed",
    "[SIMILARITY: 0.650]\n[LOG]\nConnection pool exhausted",
]


confidence = calculate_evidence_confidence(evidence)


print("Evidence confidence:", confidence)