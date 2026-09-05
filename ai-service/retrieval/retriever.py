from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

from embeddings.embedder import get_model
from chunking.chunker import chunk_text


DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DIAGNOSTIC_KEYWORDS = [
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


def retrieve_evidence(
    service: str,
    query: str,
    max_evidence: int = 5,
    similarity_threshold: float = 0.45
) -> list[str]:

    candidates = []

    # --------------------------------------------------
    # 1. Read logs
    # --------------------------------------------------

    log_file = DATA_DIR / "logs" / f"{service}.log"

    if log_file.exists():
        for line in log_file.read_text().splitlines():
            if line.strip():
                candidates.append(f"[LOG]\n{line}")

    # --------------------------------------------------
    # 2. Read metrics
    # --------------------------------------------------

    metrics_file = DATA_DIR / "metrics" / f"{service}.json"

    if metrics_file.exists():
        metrics_text = metrics_file.read_text()

        for chunk in chunk_text(metrics_text, chunk_size=100, overlap=20):
            candidates.append(f"[METRIC]\n{chunk}")

    # --------------------------------------------------
    # 3. Read deployment
    # --------------------------------------------------

    deployment_file = DATA_DIR / "deployments" / f"{service}.json"

    if deployment_file.exists():
        deployment_text = deployment_file.read_text()

        for chunk in chunk_text(deployment_text, chunk_size=100, overlap=20):
            candidates.append(f"[DEPLOYMENT]\n{chunk}")

    # --------------------------------------------------
    # 4. No candidates for this service
    # --------------------------------------------------

    if not candidates:
        print(
            f"[retriever] No data files found for service='{service}' "
            f"under {DATA_DIR}. Add data/logs/{service}.log, "
            f"data/metrics/{service}.json and/or "
            f"data/deployments/{service}.json."
        )
        return []

    # --------------------------------------------------
    # 5. Create embeddings
    # --------------------------------------------------

    model = get_model()

    query_embedding = model.encode([query])
    candidate_embeddings = model.encode(candidates)

    # --------------------------------------------------
    # 6. Calculate semantic similarity
    # --------------------------------------------------

    similarities = cosine_similarity(
        query_embedding,
        candidate_embeddings
    )[0]

    # --------------------------------------------------
    # 7. Add diagnostic relevance bonus and rank
    # --------------------------------------------------

    ranked_candidates = []

    for evidence, similarity in zip(candidates, similarities):
        text = evidence.lower()

        diagnostic_bonus = min(
            sum(0.05 for keyword in DIAGNOSTIC_KEYWORDS if keyword in text),
            0.20
        )

        final_score = similarity + diagnostic_bonus

        ranked_candidates.append((evidence, similarity, final_score))

    ranked_candidates.sort(key=lambda item: item[2], reverse=True)

    print(f"\n===== RANKING DEBUG (service='{service}') =====")
    for evidence, similarity, final_score in ranked_candidates:
        print(
            f"SIMILARITY={similarity:.3f} "
            f"FINAL={final_score:.3f} "
            f"{evidence[:120].replace(chr(10), ' ')}"
        )
    print("=========================\n")

    # --------------------------------------------------
    # 8. Filter and return evidence
    # --------------------------------------------------

    results = []

    for evidence, similarity, final_score in ranked_candidates:
        if final_score < similarity_threshold:
            continue

        results.append(f"[SIMILARITY: {similarity:.3f}]\n{evidence}")

        if len(results) >= max_evidence:
            break

    return results
