import { useState, useEffect } from "react";

export default function App() {
  const [activeTab, setActiveTab] = useState("ask"); // "ask" | "debate"
  const [selectedSessionId, setSelectedSessionId] = useState("");
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
      if (data.session_id) {
        setSelectedSessionId(data.session_id);
      }
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

  const navigateToDebate = (sessionId) => {
    if (sessionId) {
      setSelectedSessionId(sessionId);
    }
    setActiveTab("debate");
  };

  return (
    <div className="page">
      <header>
        <div className="header-top">
          <div>
            <h1>MedTrustAI</h1>
            <p>Multi-agent medical QA — 5 specialists, shared memory, debate, RAG-grounded, iterative fusion</p>
          </div>
          <div className="kb-status">{kbStatus}</div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === "ask" ? "active" : ""}`}
            onClick={() => setActiveTab("ask")}
          >
            💬 Ask MedTrustAI
          </button>
          <button
            className={`nav-tab ${activeTab === "debate" ? "active" : ""}`}
            onClick={() => setActiveTab("debate")}
          >
            ⚖️ Debate Rounds &amp; Visualizer
          </button>
        </nav>
      </header>

      <main>
        {activeTab === "ask" ? (
          <>
            <div className="ask-box">
              <textarea
                placeholder='Ask a medical question, e.g. "What are the risk factors for hypertension?"'
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <div className="ask-row">
                <button onClick={askQuestion} disabled={loading}>
                  {loading ? "Asking…" : "Ask MedTrustAI"}
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

            {result && (
              <ResultView
                data={result}
                onOpenDebate={(sid) => navigateToDebate(sid)}
              />
            )}
          </>
        ) : (
          <DebateView
            initialSessionId={selectedSessionId}
            onSelectSession={(sid) => setSelectedSessionId(sid)}
          />
        )}
      </main>

      <footer>MedTrustAI — React client → Express proxy → Python FastAPI backend</footer>
    </div>
  );
}

function ResultView({ data, onOpenDebate }) {
  const sortedAgents = [...data.agent_breakdown].sort(
    (a, b) => b.fusion_weight - a.fusion_weight
  );

  return (
    <div className="result">
      <div className="card highlight-card">
        <div className="card-top-row">
          <h2>Consensus Answer</h2>
          {data.debate_triggered && (
            <button
              className="btn-pill-action"
              onClick={() => onOpenDebate(data.session_id)}
            >
              🔍 Inspect Debate Rounds →
            </button>
          )}
        </div>
        <div className="consensus-answer">{data.consensus_answer}</div>
        <div className="consensus-reasoning">{data.consensus_reasoning}</div>
        <div className="badges">
          <span className="badge">Lead: {data.lead_agent}</span>
          <span className={`badge ${data.debate_triggered ? "debate" : ""}`}>
            {data.debate_triggered ? "⚡ Debate Triggered" : "✓ No Disagreement"}
          </span>
          <span className={`badge ${data.rag_used ? "on" : "off"}`}>
            {data.rag_used ? "📚 RAG Grounded" : "No RAG context"}
          </span>
          <span className="badge">
            Weighted confidence: {(data.fusion_weighted_confidence * 100).toFixed(0)}%
          </span>
        </div>

        <div className="session-line">
          <span>Session ID: <code>{data.session_id}</code></span>
          <button
            className="link-button"
            onClick={() => onOpenDebate(data.session_id)}
          >
            visualize debate rounds in app →
          </button>
        </div>
      </div>

      {data.rag_sources && data.rag_sources.length > 0 && (
        <div className="card">
          <h2>Retrieved Sources (RAG)</h2>
          <div className="sources">
            {data.rag_sources.map((s, i) => (
              <div className="source-chip" key={i}>
                📄 {s.source} (distance {s.distance})
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

function DebateView({ initialSessionId }) {
  const [sessionIdInput, setSessionIdInput] = useState(initialSessionId || "");
  const [loading, setLoading] = useState(false);
  const [memoryData, setMemoryData] = useState(null);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    if (initialSessionId) {
      setSessionIdInput(initialSessionId);
      loadSessionMemory(initialSessionId);
    }
  }, [initialSessionId]);

  async function loadSessionMemory(sid) {
    const id = sid || sessionIdInput.trim();
    if (!id) return;

    setLoading(true);
    setFetchError(null);

    try {
      const res = await fetch(`/api/memory/${id}`);
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }
      const data = await res.json();
      setMemoryData(data);
    } catch (e) {
      setFetchError(`Could not load session memory: ${e.message}`);
      setMemoryData(null);
    } finally {
      setLoading(false);
    }
  }

  // Group history by agent and round
  const round1Map = {};
  const round2Map = {};
  let questionText = "";

  if (memoryData && Array.isArray(memoryData.history)) {
    memoryData.history.forEach((entry) => {
      if (entry.round === 1) {
        round1Map[entry.agent] = entry;
        if (!questionText && entry.question) questionText = entry.question;
      } else if (entry.round === 2) {
        round2Map[entry.agent] = entry;
      }
    });
  }

  const agentsList = [
    "General Physician",
    "Cardiologist",
    "Neurologist",
    "Pharmacologist",
    "Evidence Reviewer",
  ];

  const hasRound2 = Object.keys(round2Map).length > 0;

  const agentIcons = {
    "General Physician": "🩺",
    Cardiologist: "🫀",
    Neurologist: "🧠",
    Pharmacologist: "💊",
    "Evidence Reviewer": "📋",
  };

  return (
    <div className="debate-page">
      {/* 1. Architecture Flow Visualizer */}
      <div className="card pipeline-card">
        <h2>🔬 How MedTrustAI Multi-Agent Debate Works</h2>
        <p className="section-subtitle">
          When specialists disagree on diagnoses, MedTrustAI initiates an automated 2-round deliberation cycle.
        </p>

        <div className="workflow-steps">
          <div className="step-card">
            <div className="step-badge">Phase 1 &amp; 2</div>
            <div className="step-icon">📚</div>
            <h3>RAG Grounding</h3>
            <p>Vector store retrieves verified medical document chunks for contextual grounding.</p>
          </div>

          <div className="step-arrow">➔</div>

          <div className="step-card">
            <div className="step-badge">Round 1</div>
            <div className="step-icon">👥</div>
            <h3>Independent Opinions</h3>
            <p>All 5 specialist agents answer concurrently &amp; persist reasoning to shared memory.</p>
          </div>

          <div className="step-arrow">➔</div>

          <div className="step-card step-highlight">
            <div className="step-badge">Threshold Engine</div>
            <div className="step-icon">⚡</div>
            <h3>Disagreement Check</h3>
            <p>Dissimilarity score computed (Jaccard word-distance). If score &ge; 0.50, Debate is triggered!</p>
          </div>

          <div className="step-arrow">➔</div>

          <div className="step-card">
            <div className="step-badge">Round 2</div>
            <div className="step-icon">⚖️</div>
            <h3>Cross-Agent Debate</h3>
            <p>Each specialist reviews all peer arguments and revises or defends their diagnosis.</p>
          </div>

          <div className="step-arrow">➔</div>

          <div className="step-card">
            <div className="step-badge">Consensus</div>
            <div className="step-icon">🏆</div>
            <h3>Iterative Fusion</h3>
            <p>Consensus weights RAG alignment and inter-agent agreement for the final answer.</p>
          </div>
        </div>
      </div>

      {/* 2. Interactive Session Debate Inspector */}
      <div className="card">
        <h2>🔍 Live Session Debate Inspector</h2>
        <p className="section-subtitle">
          Inspect round 1 initial opinions vs round 2 post-debate revisions for any session.
        </p>

        <div className="session-input-row">
          <input
            type="text"
            placeholder="Enter Session ID (e.g. 196cc75a-845d-4f5b-8116-d17577fbd8f2)"
            value={sessionIdInput}
            onChange={(e) => setSessionIdInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadSessionMemory()}
          />
          <button onClick={() => loadSessionMemory()} disabled={loading}>
            {loading ? "Loading…" : "Inspect Rounds"}
          </button>
        </div>

        {fetchError && <div className="error-box">{fetchError}</div>}

        {memoryData && (
          <div className="memory-results">
            <div className="session-overview-banner">
              <div>
                <span className="meta-label">Inspected Session:</span>{" "}
                <code>{memoryData.session_id}</code>
              </div>
              <div className="badges">
                <span className={`badge ${hasRound2 ? "debate" : ""}`}>
                  {hasRound2 ? "⚡ Round 2 Debate Executed" : "✓ Round 1 Unified Consensus"}
                </span>
                <span className="badge">
                  {memoryData.history.length} Shared Memory Records
                </span>
              </div>
            </div>

            {questionText && (
              <div className="session-question-banner">
                <strong>Original Question:</strong> "{questionText}"
              </div>
            )}

            <div className="rounds-comparison-container">
              {agentsList.map((agentName) => {
                const r1 = round1Map[agentName];
                const r2 = round2Map[agentName];
                if (!r1 && !r2) return null;

                const conf1 = r1 ? (r1.confidence * 100).toFixed(0) : null;
                const conf2 = r2 ? (r2.confidence * 100).toFixed(0) : null;
                const deltaConf = r1 && r2 ? (r2.confidence - r1.confidence) * 100 : 0;

                return (
                  <div className="agent-debate-comparison-card" key={agentName}>
                    <div className="agent-header-bar">
                      <span className="agent-title">
                        {agentIcons[agentName] || "🩺"} {agentName}
                      </span>
                      {hasRound2 && (
                        <span
                          className={`delta-badge ${
                            deltaConf > 0 ? "positive" : deltaConf < 0 ? "negative" : "neutral"
                          }`}
                        >
                          Confidence: {conf1}% ➔ {conf2}% ({deltaConf > 0 ? "+" : ""}
                          {deltaConf.toFixed(0)}%)
                        </span>
                      )}
                    </div>

                    <div className="rounds-grid">
                      {/* Round 1 Column */}
                      <div className="round-column r1-col">
                        <div className="round-tag">Round 1: Initial Stance</div>
                        {r1 ? (
                          <>
                            <div className="stance-answer">{r1.answer}</div>
                            <div className="stance-reasoning">
                              <strong>Reasoning:</strong> {r1.reasoning}
                            </div>
                            <div className="stance-footer">
                              <span>Initial Confidence: {conf1}%</span>
                            </div>
                          </>
                        ) : (
                          <div className="no-data">No Round 1 entry</div>
                        )}
                      </div>

                      {/* Arrow / Shift Indicator */}
                      {hasRound2 && (
                        <div className="debate-transition-indicator">
                          <div className="transition-icon">➔</div>
                          <span className="transition-label">Debated</span>
                        </div>
                      )}

                      {/* Round 2 Column */}
                      {hasRound2 && (
                        <div className="round-column r2-col">
                          <div className="round-tag r2-tag">Round 2: Post-Debate Revision</div>
                          {r2 ? (
                            <>
                              <div className="stance-answer">{r2.answer}</div>
                              <div className="stance-reasoning">
                                <strong>Revised Reasoning:</strong> {r2.reasoning}
                              </div>
                              <div className="stance-footer">
                                <span>Revised Confidence: {conf2}%</span>
                              </div>
                            </>
                          ) : (
                            <div className="no-data">No revision needed</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}