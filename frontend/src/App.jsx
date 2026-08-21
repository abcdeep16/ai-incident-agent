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

  const handleChange = (e) => {
    setIncident({
      ...incident,
      [e.target.name]: e.target.value,
    });
  };

  const investigate = async () => {
    setLoading(true);
    setError("");
    setResult(null);

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

      // Handle backend errors properly
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

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

  return (
    <div>
      <h1>AI Incident Agent</h1>

      <input
        name="title"
        value={incident.title}
        onChange={handleChange}
        placeholder="Incident title"
      />

      <br />
      <br />

      <input
        name="service"
        value={incident.service}
        onChange={handleChange}
        placeholder="Service name"
      />

      <br />
      <br />

      <select
        name="severity"
        value={incident.severity}
        onChange={handleChange}
      >
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
        <option value="critical">Critical</option>
      </select>

      <br />
      <br />

      <textarea
        name="description"
        value={incident.description}
        onChange={handleChange}
        placeholder="Describe the incident..."
        rows={6}
        cols={50}
      />

      <br />
      <br />

      <button onClick={investigate} disabled={loading}>
        {loading ? "Investigating..." : "Investigate"}
      </button>

      {/* Error message */}
      {error && (
        <p>
          Error: {error}
        </p>
      )}

      {/* Investigation result */}
      {result && (
        <div>
          <h2>Investigation Result</h2>

          <h3>Summary</h3>
          <p>{result.summary}</p>

          <h3>Root Cause</h3>
          <p>{result.root_cause}</p>

          <h3>Confidence</h3>
          <p>{result.confidence}</p>

          <h3>Evidence</h3>

          {result.evidence && result.evidence.length > 0 ? (
            <ul>
              {result.evidence.map((item, index) => (
                <li key={index}>
                  <strong>{item.source}</strong>
                  {" — "}
                  <span>
                    Similarity:{" "}
                    {Number(item.similarity).toFixed(2)}
                  </span>

                  <br />

                  {item.content}
                </li>
              ))}
            </ul>
          ) : (
            <p>No relevant evidence found.</p>
          )}

          <h3>Next Steps</h3>

          {result.next_steps && result.next_steps.length > 0 ? (
            <ul>
              {result.next_steps.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>No next steps available.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;