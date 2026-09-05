-- This is created automatically by backend/db.js on startup (ensureSchema()).
-- Kept here as a reference / for manual verification via psql.

CREATE TABLE IF NOT EXISTS incidents (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  service TEXT NOT NULL,
  severity TEXT NOT NULL,
  summary TEXT,
  root_cause TEXT,
  confidence NUMERIC,
  evidence JSONB,
  next_steps JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
