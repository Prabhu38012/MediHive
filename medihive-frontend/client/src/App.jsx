import { useState, useEffect } from "react";

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [kbStatus, setKbStatus] = useState("Checking knowledge base…");

  useEffect(() => {
    checkKnowledgeBase();
  }, []);

  async function checkKnowledgeBase() {
    try {
      const res = await fetch("/api/knowledge-base/status");
      const data = await res.json();
      setKbStatus(
        data.rag_active
          ? `Knowledge base active — ${data.chunks_indexed} chunks indexed`
          : "Knowledge base empty — agents answering from base knowledge only"
      );
    } catch (e) {
      setKbStatus("Could not reach server");
    }
  }

  async function askQuestion() {
    const trimmed = question.trim();
    if (!trimmed) return;

    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Server returned ${res.status}`);
      }

      setResult(data);
    } catch (e) {
      setError(`Request failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      askQuestion();
    }
  }

  return (
    <div className="page">
      <header>
        <h1>MediHive</h1>
        <p>Multi-agent medical QA — 5 specialists, shared memory, debate, RAG-grounded, iterative fusion</p>
        <div className="kb-status">{kbStatus}</div>
      </header>

      <main>
        <div className="ask-box">
          <textarea
            placeholder='Ask a medical question, e.g. "What are the risk factors for hypertension?"'
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="ask-row">
            <button onClick={askQuestion} disabled={loading}>
              {loading ? "Asking…" : "Ask MediHive"}
            </button>
          </div>
          {loading && (
            <div className="status-line">
              <span className="spinner" />
              <span>Sending to 5 agents… this can take a few minutes on local models</span>
            </div>
          )}
        </div>

        {error && <div className="error-box">{error}</div>}

        {result && <ResultView data={result} />}
      </main>

      <footer>MediHive — React client → Express proxy → Python FastAPI backend</footer>
    </div>
  );
}

function ResultView({ data }) {
  const sortedAgents = [...data.agent_breakdown].sort(
    (a, b) => b.fusion_weight - a.fusion_weight
  );

  return (
    <div className="result">
      <div className="card">
        <h2>Consensus Answer</h2>
        <div className="consensus-answer">{data.consensus_answer}</div>
        <div className="consensus-reasoning">{data.consensus_reasoning}</div>
        <div className="badges">
          <span className="badge">Lead: {data.lead_agent}</span>
          <span className={`badge ${data.debate_triggered ? "debate" : ""}`}>
            {data.debate_triggered ? "Debate triggered" : "No disagreement"}
          </span>
          <span className={`badge ${data.rag_used ? "on" : "off"}`}>
            {data.rag_used ? "RAG grounded" : "No RAG context"}
          </span>
          <span className="badge">
            Weighted confidence: {(data.fusion_weighted_confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {data.rag_sources && data.rag_sources.length > 0 && (
        <div className="card">
          <h2>Retrieved Sources (RAG)</h2>
          <div className="sources">
            {data.rag_sources.map((s, i) => (
              <div className="source-chip" key={i}>
                {s.source} (distance {s.distance})
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Agent Breakdown &amp; Fusion Weights</h2>
        <div className="agent-list">
          {sortedAgents.map((agent) => (
            <div className="agent-card" key={agent.agent}>
              <div className="agent-card-head">
                <span className="agent-name">{agent.agent}</span>
                <span className="agent-meta">
                  <span>confidence {(agent.confidence * 100).toFixed(0)}%</span>
                  <span>fusion weight {(agent.fusion_weight * 100).toFixed(0)}%</span>
                </span>
              </div>
              <div className="weight-bar-track">
                <div
                  className="weight-bar-fill"
                  style={{ width: `${(agent.fusion_weight * 100).toFixed(0)}%` }}
                />
              </div>
              <div className="agent-answer">{agent.answer}</div>
              <div className="agent-reasoning">{agent.reasoning}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
