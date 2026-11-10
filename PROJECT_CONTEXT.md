# Project Context

This document records verified behavior in the repository snapshot inspected
when this documentation was added. Source code is authoritative if this
document becomes stale.

## Purpose and current implementation

AI Incident Agent is a local-development full-stack application for submitting
an incident, retrieving related local service evidence, and returning a
structured anomaly-oriented investigation.

The current analysis path does **not** call a generative AI provider:

1. A React frontend submits incident fields to the Express backend.
2. The backend forwards a formatted prompt and service name to the FastAPI AI
   service.
3. The AI service retrieves local service logs, metrics, and deployment data
   where available.
4. A Sentence Transformers model scores the query against those local
   evidence candidates.
5. A separately trained TF-IDF + Logistic Regression pipeline classifies the
   prompt as `anomaly` or `normal`.
6. Python templates produce summary, root-cause wording, and suggested next
   steps. Evidence is returned as structured items.
7. The backend attempts to persist the result to PostgreSQL. If that fails,
   investigation still returns the analysis with a warning; history retrieval
   requires the database.

The `llm_service.py` module name and prompt wording do not indicate that a
remote LLM is used. Its implementation calls `predict_text` and returns
predefined text based on the classifier result.

## Repository areas

- `frontend/`: React 19 + Vite UI. Form, investigation output, and history UI
  are in `src/App.jsx`; styling is in `src/index.css`.
- `backend/`: Express API and PostgreSQL pool/schema bootstrap.
- `ai-service/`: FastAPI endpoints, evidence retrieval, embeddings, local
  classifier inference, and training script.
- `ai-service/artifacts/`: generated classifier, processed data, and training
  metrics in the current working tree. These files are local artifacts, not
  tracked source files in the inspected Git index.
- `data/logs/`, `data/metrics/`, `data/deployments/`: service evidence read by
  the retriever. The inspected sample data covers `payment-service`.
- `data/raw/loghub/`, `backend/data/raw/loghub/`,
  `backend/data/raw/laghub/`: raw log corpora consumed by training.
- `db/schema.sql`: reference SQL for the table created by the backend.
- `README.md`: current setup overview and commands.

## Training facts

`ai-service/train_local_model.py`:

- Reads `*.log` files directly (not recursively) from the three configured
  training directories.
- Trims blank lines, deduplicates by dataset-name plus line, then drops
  duplicate text globally before training.
- Assigns labels through substring matching against a hard-coded list of
  failure-related terms. These are heuristic labels, not human-verified
  annotations.
- Uses a stratified 80/20 train/test split with `random_state=42`.
- Trains a scikit-learn pipeline with `TfidfVectorizer` and
  `LogisticRegression`.
- Writes `log_anomaly_pipeline.joblib`, `processed_log_dataset.csv`, and
  `training_metrics.json` under `ai-service/artifacts/`.

The metrics file currently present reports 6,000 records, accuracy 0.9975,
precision 0.9845, recall 1.0, F1 0.9922, and ROC-AUC 1.0. These are results
against the heuristic labels and the random held-out split; they are not
evidence of production accuracy or independently validated incident diagnosis.

## Local commands

Commands verified from the repository README and package manifests:

```powershell
cd ai-service
python -m pip install -r requirements.txt
python train_local_model.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd backend
npm install
npm start
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults API requests to `http://localhost:5000`; set
`VITE_API_URL` to override it. The model artifact must exist before inference.
PostgreSQL is needed for saved incident history, but the backend code permits
the investigation response to succeed without persistence.

## Configuration snapshot

Configuration names visible in the code and `.env.example` files:

- Frontend: `VITE_API_URL`.
- Backend: `PORT`, `AI_SERVICE_URL`, `FRONTEND_URL`, `AI_SERVICE_TIMEOUT_MS`,
  `DATABASE_URL`, and `DATABASE_SSL`.
- AI service: `FRONTEND_URL`. `MODEL_PATH` appears in its example file, but the
  inspected `local_model_service.py` uses a fixed artifact path and does not
  read that environment variable.

`.gitignore` ignores `.env` files except `.env.example`, Python virtual
environments and bytecode, `node_modules`, and `dist`.

## Verified project status and unknowns

- Verified in code: frontend investigation and history fetches use the backend
  API; backend forwards investigations to the AI service; model and evidence
  retrieval are local code paths; PostgreSQL persistence is attempted.
- Verified in the recent local runtime session: health checks passed and an
  investigation endpoint returned a result; PostgreSQL was not configured, so
  the backend returned a persistence warning.
- Not established by this document: production deployment status, behavior
  with production data, database credentials or availability, independent
  model quality, or whether generated artifacts correspond to the current
  training sources unless retrained and checked.
- The backend package's `test` script intentionally exits with “no test
  specified”; no automated backend test suite was verified.
