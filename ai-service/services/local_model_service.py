import json
from pathlib import Path

import joblib

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "log_anomaly_pipeline.joblib"
METADATA_PATH = ARTIFACT_DIR / "training_metrics.json"


def load_model_and_metadata():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "No trained local log-anomaly model found. Run "
            "python ai-service/train_local_model.py first."
        )

    pipeline = joblib.load(MODEL_PATH)
    metadata = {}
    if METADATA_PATH.exists():
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return pipeline, metadata


def predict_text(text: str):
    pipeline, metadata = load_model_and_metadata()
    input_text = (text or "").strip()
    if not input_text:
        return {
            "prediction": "normal",
            "confidence": 0.0,
            "anomaly_probability": 0.0,
            "metadata": metadata,
        }

    probability = pipeline.predict_proba([input_text])[0]
    if probability.shape[0] == 2:
        anomaly_probability = float(probability[1])
    else:
        anomaly_probability = float(probability[0])

    prediction = "anomaly" if anomaly_probability >= 0.5 else "normal"
    confidence = float(max(probability))

    return {
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "anomaly_probability": round(anomaly_probability, 4),
        "metadata": metadata,
    }
