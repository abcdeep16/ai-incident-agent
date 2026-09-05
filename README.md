# AI Incident Agent — Fixed & Complete

## 1. ACTUAL ROOT CAUSE

`backend/server.js` required a file called `./db` twice:

```js
const db = require("./db");
const pool = require("./db");
```

**That `db.js` file was never provided in your project files** — it wasn't
shown anywhere in the documents you shared. Based on the exact error
signature you saw in the deployed backend logs:

```
ECONNREFUSED ::1:5432
ECONNREFUSED 127.0.0.1:5432
```

this is the textbook signature of `new Pool()` from `pg` being
instantiated **without** a `connectionString`. When `pg` has no
connection info, it defaults to `localhost:5432` and tries IPv6
(`::1`) first, then falls back to IPv4 (`127.0.0.1`) — exactly the two
errors you saw, in exactly that order. On Render, there is no local
Postgres running inside the backend's container, so both attempts are
refused.

In other words: **the deployed `db.js` was creating a Postgres pool
that ignored `DATABASE_URL` (or `DATABASE_URL` wasn't read at all),
so it silently fell back to `localhost`.**

I can't quote you the exact original content of `db.js` since it
wasn't in the files you sent — but the fix is unambiguous regardless
of what it contained: `db.js` must build the `Pool` from
`process.env.DATABASE_URL`, and that variable must be set in Render's
environment for the `ai-incident-backend` service (not left to a
local `.env` default). I've written a corrected `backend/db.js` below
that does this, plus SSL handling (Render's managed Postgres requires
SSL, and the backend never had SSL config either — a second, related
gap).

Two smaller, confirmed issues were also fixed:
- `ai-service/main.py` had a duplicate `CORSMiddleware` import (harmless but sloppy — removed).
- The backend called `db.query(...)` in `/api/incidents` but `pool.query(...)` everywhere else — since `db` and `pool` pointed at the same required module, this worked by accident, but it's cleaned up to consistently use `pool`.

## 2. Request flow (corrected)

```
Browser (VITE_API_URL)
  → Node backend  (/api/investigate)
      → AI service (AI_SERVICE_URL) /generate
          → retrieval (data/logs, data/metrics, data/deployments for `service`)
          → embeddings (sentence-transformers, cosine similarity)
          → Gemini (GEMINI_API_KEY)
      ← InvestigationResponse JSON
      → PostgreSQL (DATABASE_URL) — INSERT INTO incidents
  ← JSON result + incident_id
Browser renders result
```

It previously broke at the **PostgreSQL** step (backend → DB), after the
AI service had already returned a valid result — which is exactly why
you sometimes saw `AI service error` messages that weren't actually
caused by the AI service, and why `POST /generate 200 OK` could appear
in AI-service logs right before the request still failed overall.

## 3. Files changed

- `backend/db.js` — **new file**, builds `Pool` from `DATABASE_URL` with SSL, adds `ensureSchema()`
- `backend/server.js` — uses `pool` consistently, env-driven CORS (comma-separated `FRONTEND_URL`), cold-start-tolerant fetch to AI service (90s timeout instead of failing fast), returns partial success if DB write fails instead of a bare 500
- `ai-service/main.py` — removed duplicate import, `FRONTEND_URL` now supports comma-separated origins
- `ai-service/retrieval/retriever.py` — same logic, tidied
- `frontend/src/App.jsx` — small loading hint for Render free-tier cold starts, surfaces `result.warning`
- `frontend/index.html`, `frontend/src/main.jsx`, `frontend/vite.config.js` — **new files**. These are required for a Vite/React app to actually build and run and were not present in what you sent — without them `npm run dev` / `npm run build` cannot work at all.
- `db/schema.sql` — reference copy of the schema (auto-created by `ensureSchema()` on startup)
- `data/logs/payment-service.log`, `data/metrics/payment-service.json`, `data/deployments/payment-service.json` — sample data so the payment-service demo works immediately

`order-service` still has **no data files**. That's not a bug — the
retriever correctly returns "Insufficient relevant evidence" when a
service has no logs/metrics/deployments on disk. To demo a second
service, add `data/logs/order-service.log` etc. following the same
format.

## 4. Where to put your environment variables

### Local development
Copy each `.env.example` to `.env` in the same folder and fill in real values:

| File | Copy to |
|---|---|
| `backend/.env.example` | `backend/.env` |
| `ai-service/.env.example` | `ai-service/.env` |
| `frontend/.env.example` | `frontend/.env` |

These `.env` files are for your machine only — never commit them.

### Render (production)
Set these in **Render Dashboard → [service] → Environment**, not in any file:

**`ai-incident-backend` (Node):**
| Key | Value |
|---|---|
| `AI_SERVICE_URL` | `https://ai-incident-agent.onrender.com` |
| `FRONTEND_URL` | `https://ai-incident-frontend.onrender.com` |
| `DATABASE_URL` | HIDDEN — the connection string from your Render PostgreSQL instance (use the **Internal Database URL** if the DB is on Render too) |

**`ai-incident-agent` (Python/FastAPI):**
| Key | Value |
|---|---|
| `FRONTEND_URL` | `https://ai-incident-frontend.onrender.com` |
| `GEMINI_API_KEY` | HIDDEN |
| `PYTHON_VERSION` | `3.11.9` (or whatever version you've pinned) |

**`ai-incident-frontend` (Vite/Node):**
| Key | Value |
|---|---|
| `VITE_API_URL` | `https://ai-incident-backend-c816.onrender.com` |

> Vite bakes `VITE_*` vars in at **build** time. If you change `VITE_API_URL` on Render, trigger a new deploy (not just a restart) for it to take effect.

If any of `GEMINI_API_KEY`, `DATABASE_URL`, or a DB password were ever
pasted into a chat, doc, or committed to git, **rotate them** in
Render/Google AI Studio/your DB provider now — treat them as
compromised.

## 5. Build / start commands (Render)

**ai-incident-backend**
- Build command: `npm install`
- Start command: `node server.js`

**ai-incident-agent**
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  *(run this with the working directory set to `ai-service/`, i.e. Render "Root Directory" = `ai-service`)*

**ai-incident-frontend**
- Build command: `npm install && npm run build`
- Publish/output directory: `dist`

## 6. Git commands

```bash
git status
git add .
git commit -m "Fix Postgres connection (DATABASE_URL), add missing Vite scaffold, clean up CORS and AI-service timeout handling"
git push origin main
```

## 7. Verification commands

```bash
curl https://ai-incident-agent.onrender.com/health
curl https://ai-incident-backend-c816.onrender.com/health

curl -X POST https://ai-incident-backend-c816.onrender.com/api/investigate \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Payment failures\",\"service\":\"payment-service\",\"severity\":\"high\",\"description\":\"Payment requests are returning HTTP 500 errors after a recent deployment.\"}"

curl https://ai-incident-backend-c816.onrender.com/api/incidents
```

On Windows PowerShell, use `curl.exe` instead of `curl` for the above.

The backend `/health` response now also includes `databaseConfigured: true/false` — if that's `false` on Render, `DATABASE_URL` isn't set and that's your answer immediately, no guessing required.

## 8. End-to-end testing checklist

- [ ] `GET /health` on AI service returns `{"status":"ok"}`
- [ ] `GET /health` on backend returns `{"status":"ok", "databaseConfigured": true}`
- [ ] `POST /api/investigate` with `service: "payment-service"` returns a populated summary/root_cause/evidence (not "Insufficient relevant evidence")
- [ ] Backend logs show `Database schema verified/created.` on startup (proves `DATABASE_URL` works)
- [ ] `GET /api/incidents` returns the incident just created
- [ ] Frontend "Investigate Incident" renders the AI result end to end
- [ ] Frontend "View History" renders stored incidents
- [ ] Submitting `service: "order-service"` (with no data files) correctly returns "Insufficient relevant evidence" rather than crashing

## 9. Optional improvements (only after the above all pass)

- Vector database (pgvector/Pinecone) instead of in-memory cosine similarity
- Redis caching for embeddings
- Background job queue for long-running investigations
- Authentication for the dashboard
- Structured production logging / monitoring (e.g. Sentry)
- Dockerize all three services
- CI/CD pipeline (GitHub Actions → Render deploy hooks)
- Richer RAG (reranking, hybrid search)
- Agentic follow-up tool calls (e.g. auto-query live metrics APIs)
