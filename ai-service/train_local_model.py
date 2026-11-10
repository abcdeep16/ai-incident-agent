import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

DATASET_PATHS = [
    PROJECT_ROOT / "data" / "raw" / "loghub",
    PROJECT_ROOT / "backend" / "data" / "raw" / "loghub",
    PROJECT_ROOT / "backend" / "data" / "raw" / "laghub",
]

ANOMALY_PATTERNS = [
    "error",
    "fatal",
    "failed",
    "failure",
    "exception",
    "panic",
    "timeout",
    "critical",
    "segmentation",
    "crash",
    "unavailable",
    "refused",
    "kernel panic",
    "warning",
    "unable",
    "lost",
    "dropped",
    "disconnect",
    "timed out",
    "exception",
]


def find_log_files():
    for base_dir in DATASET_PATHS:
        if base_dir.exists():
            yield from sorted(base_dir.glob("*.log"))


def infer_label(line: str) -> int:
    text = (line or "").lower()
    return int(any(pattern in text for pattern in ANOMALY_PATTERNS))


def load_dataset_records():
    rows = []
    seen = set()

    for path in find_log_files():
        dataset_name = path.stem
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                signature = f"{dataset_name}::{line}"
                if signature in seen:
                    continue
                seen.add(signature)
                rows.append(
                    {
                        "dataset": dataset_name,
                        "text": line,
                        "label": infer_label(line),
                    }
                )

    if not rows:
        raise FileNotFoundError(
            "No raw log files were found under data/raw/loghub or backend/data/raw/loghub."
        )

    return pd.DataFrame(rows)


def save_artifacts(pipeline, metrics, processed_df):
    artifact_dir = ROOT / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, artifact_dir / "log_anomaly_pipeline.joblib")
    processed_df.to_csv(artifact_dir / "processed_log_dataset.csv", index=False)
    (artifact_dir / "training_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )


def build_and_train():
    df = load_dataset_records()
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)

    X = df["text"]
    y = df["label"]

    if y.nunique() < 2:
        raise ValueError(
            "The derived labels do not contain both classes. Check log parsing rules."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.95,
                    strip_accents="unicode",
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    random_state=42,
                    max_iter=5000,
                    class_weight="balanced",
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "class_distribution": {
            "normal": int((y == 0).sum()),
            "anomaly": int((y == 1).sum()),
        },
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(
            y_test,
            y_pred,
            target_names=["normal", "anomaly"],
            digits=4,
            zero_division=0,
        ),
    }

    save_artifacts(pipeline, metrics, df)
    print(json.dumps({"rows": len(df), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    build_and_train()
