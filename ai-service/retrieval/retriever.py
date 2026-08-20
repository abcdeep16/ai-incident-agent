from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def retrieve_evidence(service: str) -> list[str]:
    evidence = []

    # 1. Get up to 3 important log lines
    log_file = DATA_DIR / "logs" / f"{service}.log"

    if log_file.exists():
        lines = log_file.read_text().splitlines()

        log_matches = []

        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in [
                    "error",
                    "failed",
                    "warn",
                    "500"
                ]
            ):
                log_matches.append(line)

        evidence.extend(log_matches[:3])

    # 2. Get actual metrics
    metrics_file = DATA_DIR / "metrics" / f"{service}.json"

    if metrics_file.exists():
        metrics_data = metrics_file.read_text()

        evidence.append(
            f"Metrics:\n{metrics_data}"
        )

    # 3. Get actual deployment information
    deployment_file = DATA_DIR / "deployments" / f"{service}.json"

    if deployment_file.exists():
        deployment_data = deployment_file.read_text()

        evidence.append(
            f"Deployment:\n{deployment_data}"
        )

    return evidence[:5]