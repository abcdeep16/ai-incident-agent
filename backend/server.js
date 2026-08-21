const express = require("express");
const cors = require("cors");
require("dotenv").config();

const app = express();

// ========================================
// Environment Variables
// ========================================

const PORT = process.env.PORT || 5000;

const AI_SERVICE_URL =
  process.env.AI_SERVICE_URL || "http://127.0.0.1:8000";

const FRONTEND_URL =
  process.env.FRONTEND_URL || "http://localhost:5173";

// ========================================
// Middleware
// ========================================

app.use(
  cors({
    origin: FRONTEND_URL,
  })
);

app.use(express.json());

// ========================================
// Health Check
// ========================================

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "backend",
    aiService: AI_SERVICE_URL,
  });
});

// ========================================
// AI Investigation
// ========================================

app.post("/api/investigate", async (req, res) => {
  try {
    const {
      title,
      description,
      service,
      severity,
    } = req.body;

    // Validate request
    if (!title || !description || !service || !severity) {
      return res.status(400).json({
        error:
          "title, description, service and severity are required",
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

    console.log(
      `Investigating incident for service: ${service}`
    );

    // Call AI service
    const response = await fetch(
      `${AI_SERVICE_URL}/generate`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          prompt,
          service,
        }),
      }
    );

    // Handle AI service errors
    if (!response.ok) {
      const errorText = await response.text();

      console.error(
        "AI service returned error:",
        errorText
      );

      return res.status(response.status).json({
        error: "AI service error",
        details: errorText,
      });
    }

    // Parse AI response
    const result = await response.json();

    // Return result to frontend
    res.json(result);

  } catch (error) {
    console.error(
      "Investigation error:",
      error
    );

    res.status(500).json({
      error:
        "Failed to communicate with AI service",
    });
  }
});

// ========================================
// Start Server
// ========================================

app.listen(PORT, () => {
  console.log(
    `Backend running on port ${PORT}`
  );

  console.log(
    `AI Service: ${AI_SERVICE_URL}`
  );

  console.log(
    `Frontend: ${FRONTEND_URL}`
  );
});