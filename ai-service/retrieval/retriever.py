from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

from embeddings.embedder import model
from chunking.chunker import chunk_text


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


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

    log_lines = []

    if log_file.exists():
        log_lines = log_file.read_text().splitlines()

    for line in log_lines:
        if line.strip():
            candidates.append(
                f"[LOG]\n{line}"
            )

    # --------------------------------------------------
    # 2. Read metrics
    # --------------------------------------------------

    metrics_file = DATA_DIR / "metrics" / f"{service}.json"

    if metrics_file.exists():

        metrics_text = metrics_file.read_text()

        metrics_chunks = chunk_text(
            metrics_text,
            chunk_size=100,
            overlap=20
        )

        for chunk in metrics_chunks:
            candidates.append(
                f"[METRIC]\n{chunk}"
            )

    # --------------------------------------------------
    # 3. Read deployment
    # --------------------------------------------------

    deployment_file = DATA_DIR / "deployments" / f"{service}.json"

    if deployment_file.exists():

        deployment_text = deployment_file.read_text()

        deployment_chunks = chunk_text(
            deployment_text,
            chunk_size=100,
            overlap=20
        )

        for chunk in deployment_chunks:
            candidates.append(
                f"[DEPLOYMENT]\n{chunk}"
            )

    # --------------------------------------------------
    # 4. No candidates
    # --------------------------------------------------

    if not candidates:
        return []

    # --------------------------------------------------
    # 5. Create embeddings
    # --------------------------------------------------

    query_embedding = model.encode([query])

    candidate_embeddings = model.encode(
        candidates
    )

    # --------------------------------------------------
    # 6. Calculate semantic similarity
    # --------------------------------------------------

    similarities = cosine_similarity(
        query_embedding,
        candidate_embeddings
    )[0]

    # --------------------------------------------------
    # 7. Add diagnostic relevance bonus
    # --------------------------------------------------

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

    ranked_candidates = []

    for evidence, similarity in zip(
        candidates,
        similarities
    ):

        text = evidence.lower()

        diagnostic_bonus = 0.0

        for keyword in diagnostic_keywords:
            if keyword in text:
                diagnostic_bonus += 0.05

        # Prevent the bonus from becoming too large
        diagnostic_bonus = min(
            diagnostic_bonus,
            0.20
        )

        final_score = similarity + diagnostic_bonus

        ranked_candidates.append(
            (
                evidence,
                similarity,
                final_score
            )
        )

    # --------------------------------------------------
    # 8. Rank by final score
    # --------------------------------------------------

    ranked_candidates.sort(
        key=lambda item: item[2],
        reverse=True
    )
    print("\n===== RANKING DEBUG =====")

    for evidence, similarity, final_score in ranked_candidates:
        print(
            f"SIMILARITY={similarity:.3f} "
            f"FINAL={final_score:.3f} "
            f"{evidence[:120].replace(chr(10), ' ')}"
        )

    print("=========================\n")

    # --------------------------------------------------
    # 9. Filter and return evidence
    # --------------------------------------------------

    # --------------------------------------------------
# 9. Filter and return evidence
# --------------------------------------------------

    results = []

    for evidence, similarity, final_score in ranked_candidates:

        if final_score < similarity_threshold:
            continue

        results.append(
            f"[SIMILARITY: {similarity:.3f}]\n{evidence}"
        )

        if len(results) >= max_evidence:
            break
    return results