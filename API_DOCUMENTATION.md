# API Documentation

All paths below are verified in the current source. No authentication or
authorization middleware was found.

## Base URLs in local development

- Frontend: Vite's configured development server (commonly port `5173`).
- Backend: `http://localhost:5000` by default; configurable with `PORT`.
- AI service: `http://127.0.0.1:8000` by default; backend setting
  `AI_SERVICE_URL` can override it.

The frontend uses `VITE_API_URL` (defaults to `http://localhost:5000`).

## Backend endpoints

### `GET /health`

Returns backend process status; this does not prove that the database or AI
service is reachable.

Example response:

```json
{
  "status": "ok",
  "service": "backend",
  "aiService": "http://127.0.0.1:8000",
  "databaseConfigured": false
}
```

`databaseConfigured` reports whether `DATABASE_URL` is set, not whether the
database connection is healthy.

### `HEAD /health`

Returns HTTP 200 with no response body.

### `POST /api/investigate`

Request JSON:

```json
{
  "title": "Payment API latency spike",
  "description": "Payment requests are timing out after a deployment.",
  "service": "payment-service",
  "severity": "high"
}
```

All four values must be truthy. The backend does not restrict severity values
to a fixed enumeration. The frontend offers `low`, `medium`, `high`, and
`critical`.

Successful analysis response:

```json
{
  "summary": "Template-generated summary",
  "root_cause": "Template-generated root-cause wording",
  "confidence": 0.75,
  "evidence": [
    {
      "source": "MODEL",
      "similarity": 0.75,
      "content": "Relevant local evidence text"
    }
  ],
  "next_steps": ["Suggested next step"]
}
```

The strings above are illustrative, not guaranteed model output. In current
code, summaries/root-cause text and next steps are templates selected using
the local classifier; evidence is retrieved from local service files. If
database insertion fails, the backend still returns the analysis and adds:

```json
{
  "incident_id": null,
  "created_at": null,
  "warning": "Investigation succeeded, but the result could not be saved to the database."
}
```

When insertion succeeds, `incident_id` and `created_at` are returned.

Errors visible in the handler:

| Status | Condition | Body shape |
|---|---|---|
| `400` | One or more required fields is missing/falsey | `{ "error": "title, description, service and severity are required" }` |
| `502` | AI service cannot be reached | `{ "error": "Could not reach the AI service.", "details": "..." }` |
| `504` | AI service exceeds `AI_SERVICE_TIMEOUT_MS` (default 90,000 ms) | `{ "error": "AI service did not respond in time..." }` |
| AI status | AI service returned a non-2xx response | `{ "error": "AI service error", "details": "..." }` |
| `500` | Other investigation handler error | `{ "error": "Failed to communicate with AI service" }` |

Malformed JSON is handled by Express JSON middleware; exact response text is
provided by Express/body-parser and may vary by version.

### `GET /api/incidents`

Returns an array of saved incident rows ordered by `created_at DESC`. Row
fields are `id`, `title`, `description`, `service`, `severity`, `summary`,
`root_cause`, `confidence`, `evidence`, `next_steps`, and `created_at`.

Returns HTTP 500 with `{ "error": "Failed to fetch incidents" }` if the
database query fails.

## AI-service endpoints

### `GET /health` and `HEAD /health`

GET returns:

```json
{
  "status": "ok",
  "service": "ai-service",
  "model": "local-log-anomaly-model"
}
```

The health handler does not itself load or validate the model artifact.

### `POST /generate`

Internal backend-to-AI-service endpoint. Request model:

```json
{
  "prompt": "Formatted incident text",
  "service": "payment-service"
}
```

Both strings must be non-blank. A successful response follows the
`InvestigationResponse` model:

```json
{
  "summary": "string",
  "root_cause": "string",
  "confidence": 0.0,
  "evidence": [
    {
      "source": "string",
      "similarity": 0.0,
      "content": "string"
    }
  ],
  "next_steps": ["string"]
}
```

The schema is defined in `ai-service/models/investigation.py`.

Errors include FastAPI/Pydantic request validation responses for invalid
payloads, HTTP 400 for blank prompt/service, HTTP 500 for evidence retrieval
failure, and HTTP 502 for local inference/generation failure.

## CORS

The backend allows origins from `FRONTEND_URL` plus these local development
origins: `localhost:5173`, `localhost:5174`, `127.0.0.1:5173`, and
`127.0.0.1:5174`. The AI service independently configures CORS in
`ai-service/main.py`; its defaults include `localhost:5173` and
`localhost:5174`, but not the `127.0.0.1` variants.
