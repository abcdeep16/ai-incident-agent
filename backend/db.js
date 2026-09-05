const { Pool } = require("pg");

// ========================================
// PostgreSQL Connection
// ========================================
//
// ROOT CAUSE OF ECONNREFUSED ::1:5432 / 127.0.0.1:5432:
// node-postgres (`pg`) only connects using DATABASE_URL if you
// explicitly pass it in as `connectionString`. If Pool() is created
// with no config (or DATABASE_URL is undefined), pg silently falls
// back to its defaults: host=localhost, port=5432. On Render, there
// is no local Postgres running inside the backend container, so it
// fails first on ::1 (IPv6 localhost) then 127.0.0.1 (IPv4 localhost).
// This file fixes that by always requiring DATABASE_URL explicitly.

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error(
    "FATAL: DATABASE_URL environment variable is not set. " +
      "The backend cannot connect to PostgreSQL without it."
  );
}

// Render's managed PostgreSQL requires SSL, but its certificate chain
// is not always in Node's default trust store, so we disable strict
// verification (standard practice for Render/Heroku-style hosted PG).
const useSSL =
  process.env.DATABASE_SSL === "false"
    ? false
    : { rejectUnauthorized: false };

const pool = new Pool({
  connectionString,
  ssl: connectionString ? useSSL : false,
});

pool.on("error", (err) => {
  console.error("Unexpected PostgreSQL client error:", err);
});

// ========================================
// Schema bootstrap
// ========================================
// Creates the incidents table automatically on startup if it does not
// exist yet, so a fresh deployment doesn't require a manual migration
// step for this college project.

async function ensureSchema() {
  await pool.query(`
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
  `);
}

module.exports = pool;
module.exports.ensureSchema = ensureSchema;
