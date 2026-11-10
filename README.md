# AI Incident Agent

## Mandatory instructions for AI assistants

Before making any change in this repository, every AI assistant must read
[AI_RULES.md](./AI_RULES.md) first, then read the relevant project documents
listed there. Treat documentation as a guide, not a substitute for verifying
the current implementation. If documentation and code disagree, verify the
code and update the documentation.

Project reference documents:
[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md),
[ARCHITECTURE.md](./ARCHITECTURE.md),
[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md),
[API_DOCUMENTATION.md](./API_DOCUMENTATION.md),
[KNOWN_ISSUES.md](./KNOWN_ISSUES.md),
[DECISIONS.md](./DECISIONS.md), and
[CHANGELOG.md](./CHANGELOG.md).

This project is a full-stack incident investigation application that now uses a locally trained anomaly-detection model instead of an external AI API. The system still accepts incident submissions through the frontend and backend, but the AI analysis step is served by a local Python model trained on the repository's raw log corpora.

## Current status

- Local model training is working.
- Local inference is working through the AI service.
- External AI providers such as Gemini are no longer required.
- The backend still supports PostgreSQL-backed persistence when `DATABASE_URL` is configured, but the main investigation flow does not depend on an external LLM service.
- The project is functional in local development mode with the model-backed pipeline.

## Project goal

Use the raw log datasets in the repository to train, save, and load a local classifier that can detect abnormal incident text patterns, provide structured investigation output, and keep the application working without remote AI calls.

## Architecture

```text
Frontend (React + Vite)
    |
    v
Backend (Node.js + Express)
    |
    +--> calls local AI service at http://127.0.0.1:8000
    |
    v
AI Service (Python + FastAPI)
    |
    +--> loads saved local model artifact
    +--> preprocesses prompt text
    +--> predicts anomaly vs normal signal
    +--> returns structured investigation result
    v
(Optional) PostgreSQL for persistence when DATABASE_URL is set
```

## Data sources used for training

The model is trained on the raw system logs found in:

- `backend/data/raw/loghub/`
- `backend/data/raw/laghub/`
- `data/raw/loghub/` when present

The repository includes these log files:

- `BGL_2k.log`
- `HDFS_2k.log`
- `OpenStack_2k.log`

These are heterogeneous plain-text log corpora. The project treats them as a combined anomaly-detection corpus rather than a single tabular dataset. Each log line is normalized, deduplicated, and labeled with a rule-based anomaly heuristic based on common failure signals like `error`, `fatal`, `failed`, `exception`, `timeout`, `crash`, and related patterns.

## Training workflow

The training pipeline is implemented in `ai-service/train_local_model.py` and performs the following:

1. discovers `*.log` files directly under the supported raw data locations,
2. strips empty/duplicate log lines,
3. assigns anomaly labels using keyword-based heuristics,
4. splits the dataset into train and test subsets with stratification,
5. trains a `TF-IDF + LogisticRegression` pipeline,
6. saves the trained model and evaluation artifacts.

## Model and artifacts

Artifacts are saved under `ai-service/artifacts/`:

- `log_anomaly_pipeline.joblib` — trained local ML pipeline
- `processed_log_dataset.csv` — cleaned dataset used for training
- `training_metrics.json` — validation metrics and confusion matrix

## Inference flow

The AI service loads the saved model through `ai-service/services/local_model_service.py` and exposes a local model endpoint in `ai-service/main.py`.

- `GET /health` returns service status
- `POST /generate` accepts `{ prompt, service }` and returns a structured investigation result

The backend calls this endpoint through `backend/server.js`.

## Training results

The model was evaluated on a held-out split of the raw log corpus. The latest measured metrics are:

- accuracy: 0.9975
- precision: 0.9845
- recall: 1.0000
- F1: 0.9922
- ROC-AUC: 1.0000

These metrics are appropriate for a local prototype trained on the repository's raw log corpus. They should be treated as project-specific validation metrics rather than a production benchmark.

## Removed external AI dependencies

The project no longer depends on Gemini or any external AI API for the incident-analysis flow.

Relevant cleanup includes:

- the Python AI service uses the local model instead of remote generation,
- the dependency list no longer requires the Google AI SDK,
- `.env.example` templates do not require a remote API key for the main workflow,
- the README no longer documents a Gemini-based production path.

## Repository structure

```text
ai-incident-agent/
├── ai-service/
│   ├── artifacts/
│   │   ├── log_anomaly_pipeline.joblib
│   │   ├── processed_log_dataset.csv
│   │   └── training_metrics.json
│   ├── services/
│   │   ├── llm_service.py
│   │   └── local_model_service.py
│   ├── main.py
│   ├── requirements.txt
│   ├── train_local_model.py
│   └── .env.example
├── backend/
│   ├── db.js
│   ├── server.js
│   ├── .env.example
│   └── package.json
├── frontend/
│   └── ...
├── data/
│   └── raw/
│       └── loghub/
├── backend/data/raw/
│   └── loghub/
│   └── laghub/
├── README.md
└── LICENSE
```

## Local development quick start

### 1. Install Python dependencies

```bash
cd ai-service
python -m pip install -r requirements.txt
```

### 2. Train the local model

```bash
cd ai-service
python train_local_model.py
```

### 3. Start the AI service

```bash
cd ai-service
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 4. Start the backend

```bash
cd backend
npm install
node server.js
```

### 5. Submit a test incident

The backend exposes `/api/investigate` for incident analysis. If `DATABASE_URL` is not configured, the backend still returns AI analysis results but writes a warning instead of persisting to PostgreSQL.

## Operational notes

- The project supports local model inference without any external AI API.
- Database persistence is optional for local testing but required for full incident-history storage when configured.
- All model artifacts are saved locally so the app can operate without network access to a remote model provider.
- The current model is a practical local prototype built from raw log text, not a production-grade supervised system for a fully labeled enterprise dataset.

## Summary

The repository is now aligned with the requested local-first design: it trains a model from the raw system logs, saves all required artifacts, removes external AI API dependencies, and keeps the backend and AI service working with the locally trained model.
