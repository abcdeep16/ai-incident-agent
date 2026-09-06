# AI Incident Agent

An AI-powered production incident investigation system. A user submits an
incident (title, service, severity, description); the system retrieves
relevant evidence (logs, metrics, deployment history) using semantic
search, sends it to Gemini for root-cause analysis, and stores the result
in PostgreSQL for later review.

Live demo: `https://ai-incident-agent-frontend.onrender.com` *(may take
30–60s to respond on first load if idle — see "Uptime & Free-Tier
Behavior" below)*

---

## Architecture

```
Frontend (React + Vite, static site)
   ↓ VITE_API_URL
Backend (Node.js + Express)
   ↓ AI_SERVICE_URL
AI Service (Python + FastAPI)
   ↓
Retrieval (cosine similarity over logs/metrics/deployments)
   ↓
Gemini API (root cause analysis)
   ↓
Backend
   ↓ DATABASE_URL
PostgreSQL (Supabase)
   ↓
Frontend (renders result + incident history)
```

**Repo layout:**
```
ai-incident-agent/
├── backend/            Node.js + Express API, PostgreSQL access
├── frontend/            React + Vite dashboard UI
├── ai-service/           FastAPI service: retrieval, embeddings, Gemini
├── data/                 Sample logs/metrics/deployments per service
├── db/schema.sql          Reference copy of the incidents table schema
└── README.md
```

---

## Local setup

**Prerequisites:** Node.js 18+, Python 3.11+, a Supabase (or any) PostgreSQL
database, a Gemini API key from [Google AI Studio](https://aistudio.google.com).

```bash
# 1. AI service
cd ai-service
pip install -r requirements.txt
cp .env.example .env        # fill in GEMINI_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Backend (new terminal)
cd backend
npm install
cp .env.example .env        # fill in DATABASE_URL
node server.js

# 3. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:5000
npm run dev
```
Open the URL Vite prints (usually `http://localhost:5173`).

---

## Environment variables

| File | Key | Notes |
|---|---|---|
| `backend/.env` | `PORT` | Defaults to 5000 locally; Render sets this automatically in production — don't set it there |
| | `AI_SERVICE_URL` | AI service base URL |
| | `FRONTEND_URL` | Frontend URL(s), comma-separated if multiple, used for CORS |
| | `DATABASE_URL` | Full Postgres connection string (from Supabase → Settings → Database → URI) |
| `ai-service/.env` | `FRONTEND_URL` | Same as above |
| | `GEMINI_API_KEY` | From Google AI Studio |
| `frontend/.env` | `VITE_API_URL` | Backend base URL. Baked in at **build** time — changing it requires a rebuild, not just a restart |

**Never commit real `.env` files** — only `.env.example` files with placeholders should be tracked in git. If any real key/password was ever pasted somewhere it shouldn't have been, rotate it immediately.

---

## Render deployment

Three services, one GitHub repo:

| Service | Type | Root dir | Build command | Start command |
|---|---|---|---|---|
| AI service | Web Service (Python 3) | `ai-service` | `pip install -r requirements.txt` | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Backend | Web Service (Node) | `backend` | `npm install` | `node server.js` |
| Frontend | Static Site | `frontend` | `npm install && npm run build` | Publish dir: `dist` |

Set the environment variables from the table above in each service's
**Environment** tab on Render (production values, i.e. the actual
`.onrender.com` URLs, not `localhost`). After changing any env var,
**redeploy** that service — this is required, not automatic, especially
for the frontend since `VITE_API_URL` is compiled into the static build.

---

## Uptime & free-tier behavior

Render's free Web Services spin down after 15 minutes of inactivity and
take 30–90 seconds to wake up on the next request. **This is expected
free-tier behavior, not a bug** — the app is built to tolerate it:

- The backend uses a 90-second timeout when calling the AI service and
  returns a clear "waking up" message instead of hanging or crashing
- The frontend shows a "may take a moment to wake up" hint while loading
- The AI service retries Gemini calls automatically on transient overload

**Do not use an uptime monitor to force all services to stay awake
24/7** — Render's free plan gives **750 hours/month total, shared across
all your free Web Services combined**. Two services (backend + AI
service) pinged non-stop would consume ~1,440 hours/month, blowing past
that limit and causing Render to disable both services for the rest of
every month. Instead:

- For casual/demo use: let it sleep naturally; open both `/health` URLs
  a few minutes before a demo to pre-warm them
- For guaranteed always-on: upgrade the backend and AI service to
  Render's Starter tier (~$7/service/month) — no sleep, no hour cap
- If using an uptime monitor at all, run it only in the days around a
  scheduled demo, then pause it

---

## API reference

### `GET /health` (backend & AI service)
```json
{ "status": "ok", "service": "backend", "aiService": "...", "databaseConfigured": true }
```

### `POST /api/investigate` (backend)
**Request:**
```json
{
  "title": "Payment failures",
  "service": "payment-service",
  "severity": "high",
  "description": "Payment requests are returning HTTP 500 errors after a recent deployment."
}
```
**Response:**
```json
{
  "summary": "...",
  "root_cause": "...",
  "confidence": 0.91,
  "evidence": [{ "source": "LOG", "similarity": 0.71, "content": "..." }],
  "next_steps": ["..."],
  "incident_id": 12,
  "created_at": "2026-09-06T10:00:00.000Z"
}
```

### `GET /api/incidents` (backend)
Returns all stored incidents, most recent first.

### `POST /generate` (AI service — called by the backend, not the frontend directly)
**Request:** `{ "prompt": "...", "service": "payment-service" }`
Same response shape as `/api/investigate`, minus `incident_id`/`created_at`.

---

## Adding data for a new service

The retriever looks for exact-filename matches (case-sensitive) under `data/`:
```
data/logs/<service>.log
data/metrics/<service>.json
data/deployments/<service>.json
```
If none exist for a given `service` name, the system correctly returns
"Insufficient relevant evidence was found" rather than guessing — this is
intentional, not a bug. Add matching files to enable investigation for a
new service.

---

## Testing checklist

| # | Test | Expected |
|---|---|---|
| 1 | Investigate `payment-service` with the HTTP 500 description | Confidence > 80%, populated evidence/root cause/next steps |
| 2 | Investigate a service with no data files | "Insufficient relevant evidence", 0% confidence, HTTP 200 |
| 3 | Submit with a required field missing | HTTP 400 with a clear message |
| 4 | View History with zero incidents | "No incidents found", no crash |
| 5 | View History after several incidents | Most recent first, correct fields |
| 6 | Stop the AI service, then investigate | Backend returns 502/504, frontend shows a readable error |
| 7 | Break `DATABASE_URL`, then investigate | AI result still returned, with a `warning` about the failed save |
| 8 | `curl -I .../health` (HEAD request) | 200 OK, not 405 |

---

## Known limitations

- Service name matching is case-sensitive and exact (`payment-service` ≠ `Payment-Service`)
- Whitespace-only description fields aren't explicitly rejected, since the full prompt template is never truly empty
- Free-tier hosting means occasional cold-start delays (see above)
- Gemini model availability/pricing changes over time — if `gemini-3.6-flash` gets deprecated later, update the model name in `ai-service/services/llm_service.py`

## Resolved issues (for reference / project writeup)

This project went through a full real-world debugging cycle, useful to
mention in an interview as evidence of practical deployment experience:

1. **Backend connecting to `localhost:5432` in production** — fixed by
   ensuring `DATABASE_URL` is read explicitly in `db.js` rather than
   falling back to `pg`'s default localhost connection
2. **CORS blocking the frontend** — fixed by keeping `FRONTEND_URL` in
   sync with the frontend's actual deployed URL after redeploys
3. **UptimeRobot showing `405 Method Not Allowed`** — fixed by adding
   `HEAD` method support to both health endpoints (UptimeRobot's free
   plan always sends `HEAD`, not `GET`)
4. **Gemini `404 NOT_FOUND` on `gemini-2.5-flash`** — Google deprecated
   the model for new API accounts; fixed by switching to
   `gemini-3.6-flash` with automatic retry and a fallback model on
   transient `503` overload

## Optional future improvements

Vector database (pgvector), Redis caching, background job queue,
authentication, structured production logging/monitoring, Docker,
CI/CD, hybrid search/reranking, agentic follow-up tool calls.