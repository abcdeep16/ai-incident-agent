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
        "http://localhost:5000/api/investigate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(incident),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to investigate incident");
      }

      const data = await response.json();

      setResult(data);
    } catch (err) {
      setError(err.message);
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

      {error && <p>Error: {error}</p>}

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
          <ul>
            {result.evidence.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>

          <h3>Next Steps</h3>
          <ul>
            {result.next_steps.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;