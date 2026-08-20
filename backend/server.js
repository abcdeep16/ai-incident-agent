const express = require("express");
const cors = require("cors");
require("dotenv").config();

const app = express();
app.use(
  cors({
    origin: "http://localhost:5173",
  })
);

app.use(express.json());

const PORT = 5000;
const AI_SERVICE_URL = process.env.AI_SERVICE_URL;

// Middleware
app.use(express.json());


// Health check
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "backend",
    aiService: AI_SERVICE_URL
  });
});


// AI Investigation
app.post("/api/investigate", async (req, res) => {
  try {
    const { title, description, service, severity } = req.body;

    if (!title || !description || !service || !severity) {
      return res.status(400).json({
        error: "title, description, service and severity are required"
      });
    }

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

    const response = await fetch(
      `${AI_SERVICE_URL}/generate`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
       body: JSON.stringify({
  prompt,
  service
})
      }
    );

    if (!response.ok) {
      const error = await response.text();

      return res.status(response.status).json({
        error: "AI service error",
        details: error
      });
    }

    const result = await response.json();

    res.json(result);

  } catch (error) {
    console.error("Investigation error:", error);

    res.status(500).json({
      error: "Failed to communicate with AI service"
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});