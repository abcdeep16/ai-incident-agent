import { useState } from "react";

function App() {
  const [incident, setIncident] = useState({
    title: "",
    description: "",
    service: "",
    severity: "medium",
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [incidents, setIncidents] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  const handleChange = (e) => {
    setIncident({
      ...incident,
      [e.target.name]: e.target.value,
    });
  };

  // ========================================
  // Fetch Incident History
  // ========================================

  const fetchHistory = async () => {
    try {
      setError("");

      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/incidents`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch incident history");
      }

      const data = await response.json();

      setIncidents(data);
      setShowHistory(true);
    } catch (err) {
      console.error("History error:", err);

      setError(
        err.message || "Failed to fetch incident history"
      );
    }
  };

  // ========================================
  // Investigate Incident
  // ========================================

  const investigate = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setShowHistory(false);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/investigate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(incident),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({}));

        throw new Error(
          errorData.detail ||
            errorData.error ||
            `Request failed with status ${response.status}`
        );
      }

      const data = await response.json();

      setResult(data);
    } catch (err) {
      console.error("Investigation error:", err);

      setError(
        err.message || "Failed to investigate incident"
      );
    } finally {
      setLoading(false);
    }
  };

  const confidencePercent = Math.round(
    Number(result?.confidence || 0) * 100
  );

  return (
    <div className="app">

      {/* ========================================
          Navbar
          ======================================== */}

      <nav className="navbar">
        <div className="brand">
          <div className="brand-icon">✦</div>

          <div>
            <div className="brand-title">
              AI Incident Agent
            </div>

            <div className="brand-subtitle">
              Intelligent incident investigation
            </div>
          </div>
        </div>

        <div className="nav-status">
          <span className="status-dot"></span>
          All systems operational
        </div>
      </nav>

      <main className="dashboard">

        {/* ========================================
            Hero
            ======================================== */}

        <section className="hero">
          <span className="hero-label">
            ✦ AI-Powered Operations
          </span>

          <h1>
            Investigate incidents
            <br />
            with intelligence.
          </h1>

          <p>
            Analyze production incidents using AI,
            retrieve relevant evidence, identify likely
            root causes, and generate actionable
            remediation steps.
          </p>
        </section>

        {/* ========================================
            Main Grid
            ======================================== */}

        <div className="dashboard-grid">

          {/* ========================================
              Incident Form
              ======================================== */}

          <section className="card">

            <div className="card-header">
              <h2 className="card-title">
                New Investigation
              </h2>

              <p className="card-description">
                Describe the production incident you
                want the AI agent to investigate.
              </p>
            </div>

            <div className="card-body">

              <div className="form-group">
                <label className="form-label">
                  Incident title
                </label>

                <input
                  className="form-input"
                  name="title"
                  value={incident.title}
                  onChange={handleChange}
                  placeholder="e.g. Payment failures"
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Service
                </label>

                <input
                  className="form-input"
                  name="service"
                  value={incident.service}
                  onChange={handleChange}
                  placeholder="e.g. payment-service"
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Severity
                </label>

                <select
                  className="form-select"
                  name="severity"
                  value={incident.severity}
                  onChange={handleChange}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">
                    Critical
                  </option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Incident description
                </label>

                <textarea
                  className="form-textarea"
                  name="description"
                  value={incident.description}
                  onChange={handleChange}
                  placeholder="Describe what is happening, when it started, affected endpoints, error messages, recent deployments, etc."
                />
              </div>

              <div className="button-row">

                <button
                  className="btn btn-primary"
                  onClick={investigate}
                  disabled={loading}
                >
                  {loading
                    ? "Analyzing incident..."
                    : "Investigate Incident"}
                </button>

                <button
                  className="btn btn-secondary"
                  onClick={fetchHistory}
                >
                  View History
                </button>

              </div>

              {error && (
                <div className="error">
                  {error}
                </div>
              )}

            </div>
          </section>

          {/* ========================================
              Investigation Result
              ======================================== */}

          {result ? (
            <section className="card result-card">

              <div className="card-header">
                <h2 className="card-title">
                  AI Investigation
                </h2>

                <p className="card-description">
                  Analysis generated from incident
                  context and retrieved evidence.
                </p>
              </div>

              {/* Summary */}

              <div className="result-section">
                <h3 className="section-label">
                  Summary
                </h3>

                <p className="result-text">
                  {result.summary}
                </p>
              </div>

              {/* Root Cause */}

              <div className="result-section">
                <h3 className="section-label">
                  Likely Root Cause
                </h3>

                <p className="result-text">
                  {result.root_cause}
                </p>
              </div>

              {/* Confidence */}

              <div className="result-section">
                <h3 className="section-label">
                  Confidence
                </h3>

                <div className="confidence">

                  <span className="confidence-value">
                    {confidencePercent}%
                  </span>

                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{
                        width: `${confidencePercent}%`,
                      }}
                    />
                  </div>

                </div>
              </div>

              {/* Evidence */}

              <div className="result-section">

                <h3 className="section-label">
                  Evidence
                </h3>

                {result.evidence &&
                result.evidence.length > 0 ? (
                  <ul className="evidence-list">

                    {result.evidence.map(
                      (item, index) => (
                        <li
                          className="evidence-item"
                          key={index}
                        >

                          <div className="evidence-top">

                            <span className="evidence-source">
                              {item.source}
                            </span>

                            <span className="similarity">
                              Similarity{" "}
                              {Number(
                                item.similarity
                              ).toFixed(2)}
                            </span>

                          </div>

                          <div className="evidence-content">
                            {item.content}
                          </div>

                        </li>
                      )
                    )}

                  </ul>
                ) : (
                  <p className="result-text">
                    No relevant evidence found.
                  </p>
                )}

              </div>

              {/* Next Steps */}

              <div className="result-section">

                <h3 className="section-label">
                  Recommended Next Steps
                </h3>

                {result.next_steps &&
                result.next_steps.length > 0 ? (
                  <ul className="steps-list">

                    {result.next_steps.map(
                      (step, index) => (
                        <li
                          className="step-item"
                          key={index}
                        >

                          <span className="step-number">
                            {index + 1}
                          </span>

                          <span>{step}</span>

                        </li>
                      )
                    )}

                  </ul>
                ) : (
                  <p className="result-text">
                    No next steps available.
                  </p>
                )}

              </div>

            </section>
          ) : (
            <section className="card">

              <div className="empty">

                <div
                  style={{
                    fontSize: "32px",
                    marginBottom: "12px",
                  }}
                >
                  ✦
                </div>

                <strong>
                  Ready to investigate
                </strong>

                <p style={{ marginTop: "8px" }}>
                  Submit an incident to see AI-powered
                  root cause analysis and evidence.
                </p>

              </div>

            </section>
          )}

        </div>

        {/* ========================================
            Incident History
            ======================================== */}

        {showHistory && (
          <section className="card history-card">

            <div className="card-header">
              <h2 className="card-title">
                Incident History
              </h2>

              <p className="card-description">
                Previously investigated incidents
                stored in your database.
              </p>
            </div>

            {incidents.length === 0 ? (
              <div className="empty">
                No incidents found.
              </div>
            ) : (
              <ul className="history-list">

                {incidents.map((incident) => (

                  <li
                    className="history-item"
                    key={incident.id}
                  >

                    <h3 className="history-title">
                      {incident.title}
                    </h3>

                    <div className="history-meta">

                      <span>
                        {incident.service}
                      </span>

                      <span>•</span>

                      <span
                        className={`severity severity-${incident.severity}`}
                      >
                        {incident.severity}
                      </span>

                      <span>•</span>

                      <span>
                        Confidence{" "}
                        {Math.round(
                          Number(
                            incident.confidence
                          ) * 100
                        )}
                        %
                      </span>

                    </div>

                    <div className="history-root">
                      <strong>
                        Root cause:
                      </strong>{" "}
                      {incident.root_cause}
                    </div>

                    <div className="history-date">
                      {new Date(
                        incident.created_at
                      ).toLocaleString()}
                    </div>

                  </li>

                ))}

              </ul>
            )}

          </section>
        )}

      </main>
    </div>
  );
}

export default App;