# Architecture

## System overview

```text
Browser
  |
  | React UI, Vite development server
  | VITE_API_URL (defaults to http://localhost:5000)
  v
Express backend (:5000 by default)
  |                         \
  | POST /generate           \ PostgreSQL via pg
  v                            \ incidents table
FastAPI AI service (:8000)
  |
  +--> Retrieve service-specific local logs, metrics, deployments
  |       |
  |       +--> SentenceTransformer all-MiniLM-L6-v2 embeddings
  |       +--> cosine similarity and diagnostic keyword bonus
  |
  +--> TF-IDF + LogisticRegression classifier
  |
  +--> Template-based structured investigation response
```

## Components and responsibilities

### Frontend

`frontend/src/App.jsx` holds the incident form, sends requests to
`/api/investigate`, renders the response, and requests `/api/incidents` for
history. Its API base is `VITE_API_URL`, defaulting to `http://localhost:5000`.
Vite serves the frontend during local development.

### Backend

`backend/server.js` is the Express API. It:

- exposes `GET` and `HEAD /health`;
- validates required incident fields for `POST /api/investigate`;
- forwards a prompt and service name to the AI service;
- attempts to persist successful analyses in PostgreSQL;
- returns `GET /api/incidents` from PostgreSQL;
- applies an explicit CORS origin allowlist.

`backend/db.js` creates a `pg.Pool` using `DATABASE_URL` and provides
`ensureSchema()` to create the incidents table if possible.

### AI service

`ai-service/main.py` defines FastAPI `GET`/`HEAD /health` and `POST /generate`.
The generation route retrieves evidence and calls
`services/llm_service.py`.

`retrieval/retriever.py` loads service-specific evidence from the repository's
`data/logs`, `data/metrics`, and `data/deployments` directories. It creates
embeddings using `embeddings/embedder.py` and ranks candidates using cosine
similarity plus a bounded bonus for diagnostic keywords.

`services/local_model_service.py` loads the joblib classifier artifact and
predicts anomaly probability. `services/llm_service.py` uses that prediction
to select fixed summary, root-cause, and next-step templates. It is not a
remote LLM client in the inspected implementation.

### Training and runtime models

`train_local_model.py` produces the TF-IDF + Logistic Regression classifier
from raw `.log` files using heuristic labels. This is separate from the
Sentence Transformers model `all-MiniLM-L6-v2`, which is used only for
retrieval ranking. The embedding model is lazily initialized in process; the
classifier is loaded by `predict_text` when called.

## Investigation data flow

1. The UI posts `{ title, description, service, severity }` to the backend.
2. The backend builds a text prompt and sends `{ prompt, service }` to the AI
   service's `/generate` endpoint.
3. The AI service looks for matching service-named evidence files. It may
   return no evidence if none of those files exists.
4. The retriever ranks available evidence and returns up to five candidates.
5. The classifier predicts on the formatted prompt, not on the retrieved
   evidence.
6. The AI service returns `summary`, `root_cause`, `confidence`, `evidence`,
   and `next_steps`.
7. The backend attempts to insert the input and result into PostgreSQL. On
   insert failure, it returns the analysis with null incident identifiers and
   a `warning`; it does not discard the analysis.

## Dependencies

- Frontend: React, React DOM, Vite, React plugin, ESLint tooling (see
  `frontend/package.json`).
- Backend: Express, CORS middleware, dotenv, and node-postgres `pg` (see
  `backend/package.json`).
- AI service: FastAPI, Uvicorn, Pydantic, python-dotenv, Sentence Transformers,
  scikit-learn, NumPy, pandas, joblib, and CPU PyTorch (see
  `ai-service/requirements.txt`).
- Database: PostgreSQL, optional for returning analysis but required for
  history and successful persistence.

## Network and trust boundaries

- Frontend-to-backend and backend-to-AI are HTTP requests configured for local
  development by default.
- No authentication or authorization middleware was found on the documented
  endpoints.
- The Sentence Transformers model may need to be available in the local model
  cache or fetched by its library; offline first-run behavior was not verified.
- Database SSL behavior is controlled by `DATABASE_SSL` and the pool setup in
  `backend/db.js`.
