require("dotenv").config();

const express = require("express");
const cors = require("cors");
const pool = require("./db");
const { ensureSchema } = require("./db");

const app = express();

// ========================================
// Environment Variables
// ========================================

const PORT = process.env.PORT || 5000;

const AI_SERVICE_URL =
  process.env.AI_SERVICE_URL || "http://127.0.0.1:8000";

// Comma-separated list of allowed frontend origins.
// Example: FRONTEND_URL=https://ai-incident-frontend.onrender.com
// You can pass multiple, comma-separated, e.g.
// FRONTEND_URL=https://ai-incident-frontend.onrender.com,http://localhost:5173
const FRONTEND_URL =
  process.env.FRONTEND_URL || "http://localhost:5173";

const ALLOWED_ORIGINS = FRONTEND_URL.split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

// Always allow common local dev ports too, so local dev never breaks
// even if FRONTEND_URL in .env only lists the production URL.
const DEV_ORIGINS = [
  "http://localhost:5173",
  "http://localhost:5174",
  "http://127.0.0.1:5173",
  "http://127.0.0.1:5174",
];

const FINAL_ALLOWED_ORIGINS = Array.from(
  new Set([...ALLOWED_ORIGINS, ...DEV_ORIGINS])
);

// How long to wait for the AI service before giving up.
// Render free-tier instances can take 30-60s to wake up from an
// idle spin-down, so this is intentionally generous.
const AI_SERVICE_TIMEOUT_MS = Number(
  process.env.AI_SERVICE_TIMEOUT_MS || 90000
);

// ========================================
// Middleware
// ========================================

app.use(
  cors({
    origin: function (origin, callback) {
      // Allow requests with no origin (curl, server-to-server, health checks)
      if (!origin) return callback(null, true);

      if (FINAL_ALLOWED_ORIGINS.includes(origin)) {
        return callback(null, true);
      }

      console.warn(`Blocked CORS request from origin: ${origin}`);
      return callback(new Error("Not allowed by CORS"));
    },
  })
);

app.use(express.json());

// ========================================
// Health Check
// ========================================

app.head("/health", (req, res) => {
  res.sendStatus(200);
});

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "backend",
    aiService: AI_SERVICE_URL,
    databaseConfigured: Boolean(process.env.DATABASE_URL),
  });
});

// ========================================
// AI Investigation
// ========================================

app.post("/api/investigate", async (req, res) => {
  try {
    const { title, description, service, severity } = req.body;

    // Validate request
    if (!title || !description || !service || !severity) {
      return res.status(400).json({
        error: "title, description, service and severity are required",
      });
    }

    // Build investigation prompt
    const prompt = `
You are investigating a production incident.

Incident Title: ${title}
Service: ${service}
Severity: ${severity}

Incident Description:
${description}

Analyze this incident and provide:
1. A concise summary
2. The most likely root cause
3. Confidence score
4. Evidence
5. Recommended next steps

Do not invent evidence that was not provided.
`;

    console.log(`Investigating incident for service: ${service}`);

    // Call AI service with a generous timeout to tolerate Render
    // free-tier cold starts.
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      AI_SERVICE_TIMEOUT_MS
    );

    let response;

    try {
      response = await fetch(`${AI_SERVICE_URL}/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt, service }),
        signal: controller.signal,
      });
    } catch (fetchError) {
      if (fetchError.name === "AbortError") {
        return res.status(504).json({
          error:
            "AI service did not respond in time. It may be waking up from an idle state on Render's free tier — please try again in a moment.",
        });
      }

      console.error("Failed to reach AI service:", fetchError);

      return res.status(502).json({
        error: "Could not reach the AI service.",
        details: fetchError.message,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    // Handle AI service errors
    if (!response.ok) {
      const errorText = await response.text();

      console.error("AI service returned error:", errorText);

      return res.status(response.status).json({
        error: "AI service error",
        details: errorText,
      });
    }

    // Parse AI response
    const result = await response.json();

    // Save investigation to PostgreSQL
    let savedIncident;

    try {
      savedIncident = await pool.query(
        `
        INSERT INTO incidents (
          title,
          description,
          service,
          severity,
          summary,
          root_cause,
          confidence,
          evidence,
          next_steps
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, created_at
        `,
        [
          title,
          description,
          service,
          severity,
          result.summary,
          result.root_cause,
          result.confidence,
          JSON.stringify(result.evidence || []),
          JSON.stringify(result.next_steps || []),
        ]
      );
    } catch (dbError) {
      console.error("Failed to save incident to database:", dbError);

      // Still return the AI result to the user even if persistence
      // failed, but flag it clearly instead of a generic 500.
      return res.status(200).json({
        ...result,
        incident_id: null,
        created_at: null,
        warning:
          "Investigation succeeded, but the result could not be saved to the database.",
      });
    }

    console.log("Incident saved to database:", savedIncident.rows[0]);

    // Return result + database information
    res.json({
      ...result,
      incident_id: savedIncident.rows[0].id,
      created_at: savedIncident.rows[0].created_at,
    });
  } catch (error) {
    console.error("Investigation error:", error);

    res.status(500).json({
      error: "Failed to communicate with AI service",
    });
  }
});

// ========================================
// Incident History
// ========================================

app.get("/api/incidents", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT
        id,
        title,
        description,
        service,
        severity,
        summary,
        root_cause,
        confidence,
        evidence,
        next_steps,
        created_at
      FROM incidents
      ORDER BY created_at DESC
    `);

    res.json(result.rows);
  } catch (error) {
    console.error("Failed to fetch incidents:", error);

    res.status(500).json({
      error: "Failed to fetch incidents",
    });
  }
});

// ========================================
// Start Server
// ========================================

async function start() {
  try {
    await ensureSchema();
    console.log("Database schema verified/created.");
  } catch (error) {
    console.error(
      "Could not verify/create database schema on startup:",
      error
    );
    console.error(
      "The server will still start, but /api/investigate and /api/incidents will fail until DATABASE_URL is fixed."
    );
  }

  app.listen(PORT, () => {
    console.log(`Backend running on port ${PORT}`);
    console.log(`AI Service: ${AI_SERVICE_URL}`);
    console.log(`Allowed CORS origins: ${FINAL_ALLOWED_ORIGINS.join(", ")}`);
    console.log(
      `Database configured: ${Boolean(process.env.DATABASE_URL)}`
    );
  });
}

start();