# Database Schema

## Database

The backend uses PostgreSQL through the `pg` Node.js package. It reads
`DATABASE_URL` and creates the `incidents` table at startup with
`ensureSchema()` in `backend/db.js`. The reference definition is
`db/schema.sql`.

## `incidents`

| Column | PostgreSQL type | Nullability / default | Meaning in code |
|---|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` | Database-generated incident identifier |
| `title` | `TEXT` | `NOT NULL` | Submitted incident title |
| `description` | `TEXT` | `NOT NULL` | Submitted description |
| `service` | `TEXT` | `NOT NULL` | Service name used for evidence retrieval |
| `severity` | `TEXT` | `NOT NULL` | Submitted severity string |
| `summary` | `TEXT` | nullable | AI-service summary |
| `root_cause` | `TEXT` | nullable | AI-service root-cause text |
| `confidence` | `NUMERIC` | nullable | AI-service confidence value |
| `evidence` | `JSONB` | nullable | Serialized evidence array |
| `next_steps` | `JSONB` | nullable | Serialized list of next steps |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Insert timestamp |

## Relationships and constraints

- `id` is the only primary key.
- No foreign keys, secondary indexes, check constraints, or other tables are
  defined in the inspected schema.
- `severity` is not constrained to the frontend's four option values at the
  database layer.
- `confidence` has no database-level range constraint.
- `evidence` and `next_steps` are stored as JSONB. The backend inserts JSON
  strings for these fields.

## Persistence behavior

- Startup calls `ensureSchema()`. If database connection or schema creation
  fails, the backend logs the error and still starts listening.
- `POST /api/investigate` attempts an insert after receiving a successful AI
  response. If the insert fails, it returns the analysis with
  `incident_id: null`, `created_at: null`, and a warning.
- `GET /api/incidents` queries the table and returns HTTP 500 if the query
  fails.
- Without a working `DATABASE_URL`, history is unavailable and incident
  records are not persisted.

## Configuration

`DATABASE_URL` is used as the PostgreSQL connection string.
`DATABASE_SSL=false` disables SSL. Otherwise, when a URL exists, the pool uses
SSL with `rejectUnauthorized: false`, as defined in `backend/db.js`.

No database credentials or live connection details are documented here.
