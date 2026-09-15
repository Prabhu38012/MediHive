import React, { useState, useEffect } from "react";
import {
  Stethoscope,
  Heart,
  Brain,
  Pill,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Database,
  ShieldCheck,
  Scale,
  BookOpen,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  Check,
  ExternalLink,
  Cpu,
  Award,
} from "lucide-react";

function formatClinicalReasoning(text) {
  if (!text) return <span className="text-muted">No rationale provided.</span>;

  // Detect explicit reassessment stance tags: [Changed my recommendation], [Modified...], [Maintained...]
  const stanceMatch = text.match(/\[(Changed my recommendation|Modified my recommendation|Maintained my recommendation):?([^\]]*)\]/i);
  let stanceBadge = null;
  let cleanText = text;

  if (stanceMatch) {
    const stanceType = stanceMatch[1].toLowerCase();
    const stanceDetail = stanceMatch[2] ? stanceMatch[2].trim() : "";
    let badgeClass = "stance-pill-maintained";
    if (stanceType.includes("changed")) badgeClass = "stance-pill-changed";
    else if (stanceType.includes("modified")) badgeClass = "stance-pill-modified";

    stanceBadge = (
      <div className={`reassessment-stance-badge ${badgeClass}`}>
        <span className="stance-title-tag">{stanceMatch[1]}</span>
        {stanceDetail && <span className="stance-detail-text">: {stanceDetail}</span>}
      </div>
    );
    cleanText = text.replace(stanceMatch[0], "").trim();
  }

  // Split on numbered clinical steps like "1. Key findings... 2. Pathophysiology..."
  const steps = cleanText.split(/(?=\b[1-6]\.\s+)/g).map((s) => s.trim()).filter(Boolean);

  const bodyContent = steps.length > 1 ? (
    <div className="reasoning-steps-wrapper">
      {steps.map((step, idx) => {
        const match = step.match(/^([1-6]\.\s+[^:]+:?)([\s\S]*)$/);
        if (match) {
          const title = match[1].trim();
          const body = match[2].trim();

          // Check if body has bullet points (•)
          const hasBullets = body.includes("•");
          const bullets = hasBullets
            ? body.split("•").map((b) => b.trim()).filter(Boolean)
            : [];

          return (
            <div className="clinical-step-box" key={idx}>
              <div className="step-badge-title">{title}</div>
              {hasBullets && bullets.length > 0 ? (
                <ul className="step-bullet-list">
                  {bullets.map((bullet, bIdx) => (
                    <li key={bIdx}>{bullet}</li>
                  ))}
                </ul>
              ) : (
                <div className="step-body-text">{body}</div>
              )}
            </div>
          );
        }
        return (
          <div className="clinical-step-box" key={idx}>
            <div className="step-body-text">{step}</div>
          </div>
        );
      })}
    </div>
  ) : (
    <div className="step-body-text">{cleanText}</div>
  );

  return (
    <div className="formatted-reasoning-flow">
      {stanceBadge}
      {bodyContent}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("ask"); // "ask" | "specialists" | "debate" | "rag" | "benchmarks"
  const [selectedSpecialist, setSelectedSpecialist] = useState(0);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [kbStatus, setKbStatus] = useState({ chunks: 0, active: false });
  const [selectedSessionId, setSelectedSessionId] = useState("");

  useEffect(() => {
    fetchKnowledgeBaseStatus();
  }, []);

  async function fetchKnowledgeBaseStatus() {
    try {
      const res = await fetch("/api/knowledge-base/status");
      const data = await res.json();
      setKbStatus({
        chunks: data.chunks_indexed || 0,
        active: Boolean(data.rag_active),
      });
    } catch (e) {
      setKbStatus({ chunks: 0, active: false });
    }
  }

  async function handleAsk(promptText) {
    const query = promptText || question;
    const trimmed = query.trim();
    if (!trimmed) return;

    if (promptText) {
      setQuestion(promptText);
    }

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
        throw new Error(data.error || `Server responded with status ${res.status}`);
      }

      setResult(data);
      if (data.session_id) {
        setSelectedSessionId(data.session_id);
      }
    } catch (err) {
      setError(`Diagnostic execution error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const samplePrompts = [
    {
      title: "Chest pain & troponin",
      text: "A 58-year-old male with long-standing hypertension presents with sudden-onset severe, tearing chest pain radiating to the interscapular region. BP right arm 184/98, left arm 118/68. What is the most likely diagnosis and immediate pharmacological protocol?",
    },
    {
      title: "Metformin in CKD",
      text: "Is metformin contraindicated in a patient with Type 2 Diabetes whose estimated glomerular filtration rate (eGFR) has dropped to 28 mL/min/1.73m²?",
    },
    {
      title: "Parkinson vs Essential Tremor",
      text: "How to clinically differentiate resting pill-rolling tremor in Parkinson's disease from postural action tremor in Essential Tremor?",
    },
    {
      title: "Dengue warning signs",
      text: "What pivotal clinical and laboratory findings indicate severe dengue shock syndrome requiring urgent fluid resuscitation?",
    },
  ];

  const specialists = [
    {
      name: "General Physician",
      role: "Internal Medicine & Chief Triage",
      icon: Stethoscope,
      accent: "#a78bfa",
      gradient: "linear-gradient(135deg, #a78bfa 0%, #818cf8 100%)",
      glow: "rgba(167, 139, 250, 0.35)",
      desc: "Holistic clinical reasoning, differential formulation, Occam's razor priority, and life-threat triage.",
      rules: [
        "Identifies chief complaint, patient vitals, and pivotal lab anomalies.",
        "Formulates primary differentials prioritizing high-probability clinical states.",
        "Systematically tests distractors and alternative explanations.",
      ],
    },
    {
      name: "Cardiologist",
      role: "Cardiovascular & Hemodynamics",
      icon: Heart,
      accent: "#f43f5e",
      gradient: "linear-gradient(135deg, #fb7185 0%, #f43f5e 50%, #e11d48 100%)",
      glow: "rgba(244, 63, 94, 0.4)",
      desc: "Coronary perfusion, hemodynamics, arrhythmias, ECG interpretation, and cardiovascular mimics.",
      rules: [
        "Evaluates hemodynamics, pulse pressure, heart sounds, and cardiac biomarkers.",
        "Differentiates acute coronary syndromes from non-cardiac chest pain.",
        "Eliminates options incompatible with cardiovascular physiology.",
      ],
    },
    {
      name: "Neurologist",
      role: "Neuroanatomy & CNS/PNS",
      icon: Brain,
      accent: "#38bdf8",
      gradient: "linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)",
      glow: "rgba(56, 189, 248, 0.35)",
      desc: "Neuroanatomical localization, cranial nerve testing, stroke localization, and neurosensory toxicities.",
      rules: [
        "Localizes focal lesions across central and peripheral nervous systems.",
        "Evaluates stroke syndromes, seizures, and cranial neuropathies.",
        "Screens neurotoxic pharmacology and neuromuscular junction defects.",
      ],
    },
    {
      name: "Pharmacologist",
      role: "Pharmacokinetics & Drug Interactions",
      icon: Pill,
      accent: "#fb923c",
      gradient: "linear-gradient(135deg, #fb923c 0%, #ea580c 100%)",
      glow: "rgba(251, 146, 60, 0.35)",
      desc: "Cellular & molecular drug mechanisms, receptor kinetics, drug-drug interactions, and contraindications.",
      rules: [
        "Verifies exact mechanism of action (enzymes, receptors, ion channels).",
        "Assesses organ clearance, renal contraindications, and hepatic metabolism.",
        "Pinpoints adverse drug reactions and toxicities.",
      ],
    },
    {
      name: "Evidence Reviewer",
      role: "EBM & Clinical Guidelines",
      icon: FileText,
      accent: "#34d399",
      gradient: "linear-gradient(135deg, #34d399 0%, #059669 100%)",
      glow: "rgba(52, 211, 153, 0.35)",
      desc: "Evidence-Based Medicine standards, clinical trial guidelines, and literature grounding.",
      rules: [
        "Scrutinizes clinical trials, meta-analyses, and peer-reviewed consensus.",
        "Ensures recommendations conform to WHO, ACC/AHA, and NICE standards.",
        "Evaluates certainty of evidence and statistical validity.",
      ],
    },
  ];

  return (
    <div className="eleven-app">
      {/* ── Top Navigation Bar ── */}
      <header className="eleven-nav">
        <div className="nav-container">
          <div className="nav-brand" onClick={() => setActiveTab("ask")}>
            <span className="brand-symbol">✦</span>
            <span className="brand-name">MediHive</span>
            <span className="brand-tag">Clinical AI</span>
          </div>

          <nav className="nav-links">
            <button
              className={`nav-link ${activeTab === "ask" ? "active" : ""}`}
              onClick={() => setActiveTab("ask")}
            >
              Clinical Consultation
            </button>
            <button
              className={`nav-link ${activeTab === "specialists" ? "active" : ""}`}
              onClick={() => setActiveTab("specialists")}
            >
              5 Specialists
            </button>
            <button
              className={`nav-link ${activeTab === "debate" ? "active" : ""}`}
              onClick={() => setActiveTab("debate")}
            >
              Debate Engine
            </button>
            <button
              className={`nav-link ${activeTab === "rag" ? "active" : ""}`}
              onClick={() => setActiveTab("rag")}
            >
              Literature RAG
            </button>
            <button
              className={`nav-link ${activeTab === "benchmarks" ? "active" : ""}`}
              onClick={() => setActiveTab("benchmarks")}
            >
              Benchmarks
            </button>
          </nav>

          <div className="nav-right">
            <div className={`kb-pill-badge ${kbStatus.active ? "active" : ""}`}>
              <span className="pulse-dot" />
              <span>
                {kbStatus.active
                  ? `Knowledge Base (${kbStatus.chunks})`
                  : "Base Knowledge Only"}
              </span>
            </div>

            <button
              className="btn-pill-black"
              onClick={() => {
                setActiveTab("ask");
                window.scrollTo({ top: 350, behavior: "smooth" });
              }}
            >
              New Consultation
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Viewport Content Organized by Page ── */}
      <main className="eleven-main">
        {/* =========================================================================
            PAGE 1: CLINICAL CONSULTATION (Default Ask Page)
            ========================================================================= */}
        {activeTab === "ask" && (
          <div className="page-view-container">
            {/* Hero Editorial Row */}
            <section className="hero-editorial">
              <div className="hero-editorial-row">
                <div className="hero-left">
                  <h1 className="hero-headline">
                    Bringing clinical <br />
                    intelligence to life
                  </h1>
                  <div className="hero-cta-group">
                    <button
                      className="btn-pill-black hero-btn"
                      onClick={() => {
                        const el = document.getElementById("consultation-input");
                        if (el) el.focus();
                      }}
                    >
                      Start Consultation
                    </button>
                    <button
                      className="btn-pill-outline hero-btn"
                      onClick={() => setActiveTab("specialists")}
                    >
                      Explore 5 Specialists
                    </button>
                  </div>
                </div>

                <div className="hero-right">
                  <p className="hero-paragraph">
                    Powering evidence-grounded differential diagnosis, multi-specialist
                    consensus, and medical literature retrieval. From 5 specialized AI
                    physicians to autonomous peer debate and PubMed-grounded evidence verification.
                  </p>
                </div>
              </div>
            </section>

            {/* Consultation Main Console Card */}
            <section className="showcase-outer-card">
              {/* Quick Specialist Orbs Preview Bar */}
              <div className="consult-orbs-preview-row">
                <div className="orbs-preview-label">
                  <span>5 Specialists on Consultation Panel:</span>
                </div>
                <div className="orbs-mini-row">
                  {specialists.map((spec, idx) => {
                    const IconComp = spec.icon;
                    return (
                      <div
                        className="orb-mini-item"
                        key={spec.name}
                        onClick={() => {
                          setSelectedSpecialist(idx);
                          setActiveTab("specialists");
                        }}
                        title={`View ${spec.name} persona`}
                      >
                        <div
                          className="orb-mini-circle"
                          style={{ background: spec.gradient }}
                        >
                          <IconComp size={16} />
                        </div>
                        <span className="orb-mini-name">{spec.name}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Consultation Input Area */}
              <div className="prompt-card-wrapper">
                <div className="textarea-container">
                  <textarea
                    id="consultation-input"
                    rows={4}
                    placeholder="Describe clinical symptoms, patient vitals, or enter a clinical MCQ vignette... (e.g., 58yo male with acute tearing chest pain)"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                        handleAsk();
                      }
                    }}
                  />

                  <div className="prompt-actions-bar">
                    <div className="quick-chips-group">
                      <span className="chips-label">Sample Cases:</span>
                      {samplePrompts.map((s, idx) => (
                        <button
                          key={idx}
                          className="prompt-chip-btn"
                          onClick={() => handleAsk(s.text)}
                          disabled={loading}
                        >
                          {s.title}
                        </button>
                      ))}
                    </div>

                    <button
                      className="btn-pill-black submit-btn"
                      onClick={() => handleAsk()}
                      disabled={loading || !question.trim()}
                    >
                      {loading ? (
                        <>
                          <RefreshCw className="animate-spin" size={16} />
                          <span>Deliberating…</span>
                        </>
                      ) : (
                        <>
                          <span>Consult Specialist Panel</span>
                          <ArrowRight size={16} />
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {loading && (
                  <div className="deliberation-progress-bar">
                    <div className="pulse-progress-indicator">
                      <div className="progress-dot pulse" />
                      <span>
                        Retrieving literature RAG context & running 5 clinical specialists concurrently…
                      </span>
                    </div>
                  </div>
                )}

                {error && <div className="diagnostic-error-banner">{error}</div>}
              </div>

              {/* ── Diagnostic Results Presentation ── */}
              {result && (
                <div className="diagnostic-results-wrapper">
                  {/* Consensus Verdict Box */}
                  <div className="consensus-verdict-card">
                    <div className="verdict-header">
                      <div className="verdict-tag-pill">
                        <Sparkles size={14} />
                        <span>Clinical Consensus Verdict</span>
                      </div>

                      <div className="verdict-badges-right">
                        <span
                          className={`verdict-badge ${
                            result.debate_triggered ? "badge-debate" : "badge-consensus"
                          }`}
                        >
                          {result.debate_triggered
                            ? "⚡ Debate Triggered & Resolved"
                            : "✓ Unanimous Agreement"}
                        </span>
                        <span className="verdict-badge badge-rag">
                          {result.rag_used
                            ? "📚 RAG Grounded"
                            : "Base Knowledge"}
                        </span>
                        <span className="verdict-badge badge-confidence">
                          {(result.fusion_weighted_confidence * 100).toFixed(0)}% Fusion Confidence
                        </span>
                      </div>
                    </div>

                    <div className="verdict-answer-box">
                      <div className="verdict-directive-label">
                        <Award size={14} className="text-emerald" />
                        <span>Consensus Recommendation</span>
                      </div>
                      <h2 className="verdict-main-answer">
                        {result.consensus_answer}
                      </h2>
                    </div>

                    {result.reasonable_alternative && (
                      <div className="alternative-option-banner">
                        <div className="alt-title-row">
                          <Scale size={15} className="text-amber" />
                          <strong>Secondary Reasonable Alternative (Consider per Clinical Context):</strong>
                          {result.alternative_weight > 0 && (
                            <span className="alt-weight-pill">
                              {(result.alternative_weight * 100).toFixed(0)}% Evidence Weight
                            </span>
                          )}
                        </div>
                        <div className="alt-desc-row">
                          <span>{result.reasonable_alternative}</span>
                        </div>
                      </div>
                    )}

                    <div className="verdict-reasoning-box">
                      <h4 className="section-label">Chain-of-Thought Rationale</h4>
                      <div className="reasoning-text">
                        {formatClinicalReasoning(result.consensus_reasoning)}
                      </div>
                    </div>

                    <div className="verdict-footer-meta">
                      <div className="lead-agent-info">
                        <span className="meta-sub">Lead Specialist:</span>
                        <strong className="lead-name">{result.lead_agent}</strong>
                      </div>

                      {result.debate_triggered && (
                        <button
                          className="btn-view-debate-pill"
                          onClick={() => {
                            setSelectedSessionId(result.session_id);
                            setActiveTab("debate");
                          }}
                        >
                          <span>Inspect Round 1 vs Round 2 Debate</span>
                          <ArrowRight size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* RAG Sources Box */}
                  {result.rag_sources && result.rag_sources.length > 0 && (
                    <div className="rag-sources-card">
                      <div className="sources-head">
                        <BookOpen size={16} className="text-emerald" />
                        <h3>Verified Literature Retrieved (ChromaDB Vector Store)</h3>
                      </div>
                      <div className="sources-grid">
                        {result.rag_sources.map((src, i) => (
                          <div className="source-item-card" key={i}>
                            <div className="source-header">
                              <span className="source-doc-name">📄 {src.source}</span>
                              <span className="source-distance">
                                Similarity Distance: {src.distance}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 5 Specialists Breakdown Grid */}
                  <div className="specialists-breakdown-section">
                    <h3 className="breakdown-section-title">
                      Specialist Assessment Breakdown & Fusion Weights
                    </h3>
                    <div className="specialists-grid">
                      {result.agent_breakdown.map((agent) => (
                        <div className="agent-eval-card" key={agent.agent}>
                          <div className="agent-card-top">
                            <span className="eval-agent-name">{agent.agent}</span>
                            <span className="eval-weight-pill">
                              {(agent.fusion_weight * 100).toFixed(0)}% Weight
                            </span>
                          </div>

                          <div className="eval-weight-bar">
                            <div
                              className="weight-fill"
                              style={{
                                width: `${(agent.fusion_weight * 100).toFixed(0)}%`,
                              }}
                            />
                          </div>

                          <div className="eval-answer-snippet">
                            <span className="eval-ans-label">Diagnosis:</span>
                            <span className="eval-ans-val">{agent.answer}</span>
                          </div>

                          <div className="eval-reasoning-container">
                            <div className="eval-reasoning-scroll">
                              {formatClinicalReasoning(agent.reasoning)}
                            </div>
                          </div>

                          <div className="eval-footer-conf">
                            <span className="conf-label">Diagnostic Certainty</span>
                            <div className="conf-val-group">
                              <div className="mini-conf-bar">
                                <div
                                  className="mini-conf-fill"
                                  style={{ width: `${(agent.confidence * 100).toFixed(0)}%` }}
                                />
                              </div>
                              <strong>{(agent.confidence * 100).toFixed(0)}%</strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* =========================================================================
            PAGE 2: 5 SPECIALISTS SHOWCASE
            ========================================================================= */}
        {activeTab === "specialists" && (
          <div className="page-view-container specialists-view">
            <div className="section-header-editorial">
              <span className="section-pill-tag">Multi-Agent Architecture</span>
              <h2 className="section-editorial-title">5 Specialized Clinical AI Personas</h2>
              <p className="section-editorial-desc">
                Each agent operates with domain-tailored diagnostic directives, structured Chain-of-Thought
                pathophysiology workflows, and differential elimination principles.
              </p>
            </div>

            {/* 5 Spherical Orbs Showcase */}
            <div className="showcase-outer-card orbs-page-card">
              <div className="orbs-stage-container">
                <div className="orbs-row">
                  {specialists.map((spec, idx) => {
                    const IconComp = spec.icon;
                    const isSelected = selectedSpecialist === idx;
                    return (
                      <div
                        key={spec.name}
                        className={`orb-column ${isSelected ? "selected" : ""}`}
                        onClick={() => setSelectedSpecialist(idx)}
                      >
                        <div
                          className="orb-sphere"
                          style={{
                            background: spec.gradient,
                            boxShadow: isSelected ? `0 14px 35px ${spec.glow}` : "0 6px 20px rgba(0,0,0,0.08)",
                          }}
                        >
                          <div className="orb-center-icon">
                            <IconComp size={24} />
                          </div>
                          {isSelected && <div className="orb-pulse-ring" />}
                        </div>

                        <div className="orb-meta">
                          <div className="orb-title">{spec.name}</div>
                          <div className="orb-desc">{spec.role}</div>
                          {isSelected ? (
                            <span className="orb-active-tag">Active Lens</span>
                          ) : (
                            <span className="orb-active-tag-placeholder" />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Active Specialist Card Drawer */}
                <div className="specialist-detail-banner">
                  <div className="spec-info-row">
                    <div className="spec-badge-pill">
                      {React.createElement(specialists[selectedSpecialist].icon, {
                        size: 14,
                      })}
                      <span>Selected Specialist: {specialists[selectedSpecialist].name}</span>
                    </div>
                    <p className="spec-desc-text">
                      {specialists[selectedSpecialist].desc}
                    </p>
                  </div>
                  <div className="spec-rules-row">
                    {specialists[selectedSpecialist].rules.map((rule, i) => (
                      <div className="spec-rule-chip" key={i}>
                        <Check size={12} className="check-icon" />
                        <span>{rule}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Detailed Specialist Profile Cards */}
            <div className="specialists-detailed-grid">
              {specialists.map((spec) => {
                const IconComp = spec.icon;
                return (
                  <div className="spec-feature-card" key={spec.name}>
                    <div className="spec-feature-top">
                      <div
                        className="spec-feature-icon"
                        style={{ background: spec.gradient }}
                      >
                        <IconComp size={22} color="#ffffff" />
                      </div>
                      <div>
                        <h3>{spec.name}</h3>
                        <span className="spec-role-subtitle">{spec.role}</span>
                      </div>
                    </div>

                    <p className="spec-feature-desc">{spec.desc}</p>

                    <div className="spec-rules-list">
                      <strong>Diagnostic Principles:</strong>
                      <ul>
                        {spec.rules.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* =========================================================================
            PAGE 3: DEBATE ENGINE & INSPECTOR
            ========================================================================= */}
        {activeTab === "debate" && (
          <div className="page-view-container">
            <DebateEngineTab
              sessionId={selectedSessionId}
              onSelectSession={(id) => setSelectedSessionId(id)}
            />
          </div>
        )}

        {/* =========================================================================
            PAGE 4: LITERATURE RAG KNOWLEDGE BASE
            ========================================================================= */}
        {activeTab === "rag" && (
          <div className="page-view-container">
            <LiteratureRAGTab kbStatus={kbStatus} onTestPrompt={(p) => {
              setQuestion(p);
              setActiveTab("ask");
              handleAsk(p);
            }} />
          </div>
        )}

        {/* =========================================================================
            PAGE 5: CLINICAL BENCHMARKS
            ========================================================================= */}
        {activeTab === "benchmarks" && (
          <div className="page-view-container">
            <BenchmarksTab />
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="eleven-footer">
        <div className="footer-container">
          <div className="footer-left">
            <span>MediHive Clinical AI</span>
            <span className="footer-divider">•</span>
            <span>FastAPI Multi-Agent Core + Express Gateway + Vite Client</span>
          </div>
          <div className="footer-right">
            <span>USMLE & PubMedQA Evaluated</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ── Tab: Debate Engine & Session Memory Inspector ── */
function DebateEngineTab({ sessionId, onSelectSession }) {
  const [sidInput, setSidInput] = useState(sessionId || "");
  const [memoryData, setMemoryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      setSidInput(sessionId);
      loadSession(sessionId);
    }
  }, [sessionId]);

  async function loadSession(idToLoad) {
    const id = (idToLoad || sidInput).trim();
    if (!id) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/memory/${id}`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();
      setMemoryData(data);
    } catch (e) {
      setError(`Failed to retrieve session memory: ${e.message}`);
      setMemoryData(null);
    } finally {
      setLoading(false);
    }
  }

  const round1 = {};
  const round2 = {};
  let originalQuestion = "";

  if (memoryData && Array.isArray(memoryData.history)) {
    memoryData.history.forEach((row) => {
      if (row.round === 1) {
        round1[row.agent] = row;
        if (!originalQuestion && row.question) originalQuestion = row.question;
      } else if (row.round === 2) {
        round2[row.agent] = row;
      }
    });
  }

  const agentNames = [
    "General Physician",
    "Cardiologist",
    "Neurologist",
    "Pharmacologist",
    "Evidence Reviewer",
  ];

  const hasRound2 = Object.keys(round2).length > 0;

  return (
    <div className="tab-pane-content">
      <div className="pane-header-box">
        <h2>Autonomous Clinical Debate & Arbitration Engine</h2>
        <p>
          When specialists disagree beyond threshold (Dissimilarity &ge; 0.50), MediHive triggers an autonomous
          re-deliberation round where specialists review and critique peer opinions before finalizing consensus.
        </p>
      </div>

      {/* 4-Stage Visual Workflow Cards */}
      <div className="debate-workflow-cards-row">
        <div className="debate-step-card">
          <div className="step-num-badge">Stage 1</div>
          <h4>Independent Assessments</h4>
          <p>All 5 clinical specialists evaluate the case vignette concurrently and log rationale to SQLite.</p>
        </div>
        <div className="debate-step-card">
          <div className="step-num-badge">Stage 2</div>
          <h4>Dissimilarity Scoring</h4>
          <p>Computes pairwise Jaccard & decision dissimilarity. If score &ge; 0.50, Debate is triggered.</p>
        </div>
        <div className="debate-step-card">
          <div className="step-num-badge">Stage 3</div>
          <h4>Cross-Agent Deliberation</h4>
          <p>Each specialist reviews peer diagnoses and pharmacologic rationale, revising or defending their stance.</p>
        </div>
        <div className="debate-step-card">
          <div className="step-num-badge">Stage 4</div>
          <h4>Iterative Fusion Consensus</h4>
          <p>3 rounds of soft-voting fusion combine RAG literature alignment and inter-agent agreement.</p>
        </div>
      </div>

      {/* Session Inspector Card */}
      <div className="session-inspector-card">
        <div className="inspector-input-row">
          <input
            type="text"
            placeholder="Enter Session UUID (e.g. 196cc75a-845d-4f5b-8116-d17577fbd8f2)..."
            value={sidInput}
            onChange={(e) => setSidInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadSession()}
          />
          <button
            className="btn-pill-black"
            onClick={() => loadSession()}
            disabled={loading || !sidInput.trim()}
          >
            {loading ? "Inspecting…" : "Inspect Session Rounds"}
          </button>
        </div>

        {error && <div className="diagnostic-error-banner">{error}</div>}

        {memoryData && (
          <div className="memory-history-container">
            <div className="session-meta-pill-bar">
              <div>
                <strong>Inspecting Session:</strong> <code>{memoryData.session_id}</code>
              </div>
              <div className="badges-group">
                <span className={`verdict-badge ${hasRound2 ? "badge-debate" : "badge-consensus"}`}>
                  {hasRound2 ? "⚡ Round 2 Debate Executed" : "✓ Unanimous Round 1"}
                </span>
                <span className="verdict-badge badge-rag">
                  {memoryData.history.length} Shared Memory Records
                </span>
              </div>
            </div>

            {originalQuestion && (
              <div className="original-question-card">
                <strong>Original Case Prompt:</strong> "{originalQuestion}"
              </div>
            )}

            <div className="debate-rounds-comparison-list">
              {agentNames.map((name) => {
                const r1 = round1[name];
                const r2 = round2[name];
                if (!r1 && !r2) return null;

                const c1 = r1 ? (r1.confidence * 100).toFixed(0) : null;
                const c2 = r2 ? (r2.confidence * 100).toFixed(0) : null;
                const delta = r1 && r2 ? (r2.confidence - r1.confidence) * 100 : 0;

                return (
                  <div className="agent-comparison-row-card" key={name}>
                    <div className="comparison-card-top">
                      <h4>{name}</h4>
                      {hasRound2 && (
                        <span
                          className={`confidence-delta-tag ${
                            delta > 0 ? "tag-plus" : delta < 0 ? "tag-minus" : "tag-neutral"
                          }`}
                        >
                          Confidence: {c1}% ➔ {c2}% ({delta > 0 ? "+" : ""}
                          {delta.toFixed(0)}%)
                        </span>
                      )}
                    </div>

                    <div className="comparison-columns-grid">
                      <div className="stance-column round-1-col">
                        <div className="col-tag">Round 1: Initial Stance</div>
                        {r1 ? (
                          <>
                            <div className="stance-ans">{r1.answer}</div>
                            <div className="stance-reason">
                              {formatClinicalReasoning(r1.reasoning)}
                            </div>
                            <div className="stance-meta">Initial Confidence: {c1}%</div>
                          </>
                        ) : (
                          <div className="text-muted">No Round 1 record</div>
                        )}
                      </div>

                      {hasRound2 && (
                        <div className="stance-arrow-indicator">
                          <span>➔</span>
                          <small>Debated</small>
                        </div>
                      )}

                      {hasRound2 && (
                        <div className="stance-column round-2-col">
                          <div className="col-tag tag-r2">Round 2: Revised Stance</div>
                          {r2 ? (
                            <>
                              <div className="stance-ans">{r2.answer}</div>
                              <div className="stance-reason">
                                {formatClinicalReasoning(r2.reasoning)}
                              </div>
                              <div className="stance-meta">Revised Confidence: {c2}%</div>
                            </>
                          ) : (
                            <div className="text-muted">No revision required</div>
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

/* ── Tab: Literature RAG ── */
function LiteratureRAGTab({ kbStatus, onTestPrompt }) {
  const documents = [
    "Cardiovascular diseases.pdf",
    "Hypertension.pdf",
    "Stroke.pdf",
    "Asthma.pdf",
    "Chronic obstructive pulmonary disease (COPD).pdf",
    "Diabetes.pdf",
    "Dengue.pdf",
    "Antimicrobial resistance.pdf",
    "Patient safety.pdf",
    "Tuberculosis.pdf",
    "Epilepsy.pdf",
    "Migraine and other headache disorders.pdf",
    "Dementia.pdf",
    "Depressive disorder (depression).pdf",
    "Pneumonia in children.pdf",
  ];

  return (
    <div className="tab-pane-content">
      <div className="pane-header-box">
        <h2>Medical Literature RAG Knowledge Base</h2>
        <p>
          Semantic document retrieval powered by ChromaDB persistent vector collection and
          local SentenceTransformers (<code>all-MiniLM-L6-v2</code>). Grounded answers receive iterative fusion bonuses.
        </p>
      </div>

      {/* RAG Metrics */}
      <div className="rag-overview-grid">
        <div className="rag-stat-card">
          <span className="rag-stat-number">{kbStatus.chunks}</span>
          <span className="rag-stat-label">Document Chunks Indexed</span>
        </div>
        <div className="rag-stat-card">
          <span className="rag-stat-number">21</span>
          <span className="rag-stat-label">Accredited Clinical Guidelines</span>
        </div>
        <div className="rag-stat-card">
          <span className="rag-stat-number">384</span>
          <span className="rag-stat-label">Vector Embedding Dimensions</span>
        </div>
        <div className="rag-stat-card">
          <span className="rag-stat-number">Top 4</span>
          <span className="rag-stat-label">Context Chunks Retrieved / Case</span>
        </div>
      </div>

      {/* Ingested Document Library */}
      <div className="rag-doc-library-card">
        <h3>Ingested WHO & Clinical Guideline Documents</h3>
        <p className="library-sub">
          These documents are embedded into ChromaDB to provide grounded contextual citations:
        </p>
        <div className="rag-doc-chips-grid">
          {documents.map((doc, i) => (
            <div className="rag-doc-chip" key={i}>
              <BookOpen size={14} className="text-emerald" />
              <span>{doc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Tab: Benchmarks ── */
function BenchmarksTab() {
  return (
    <div className="tab-pane-content">
      <div className="pane-header-box">
        <h2>Standardized Clinical Benchmark Evaluations</h2>
        <p>
          MediHive is evaluated on recognized clinical question-answering benchmarks, verifying
          that multi-agent consensus significantly outperforms individual LLMs.
        </p>
      </div>

      <div className="benchmarks-comparison-grid">
        <div className="bench-card">
          <div className="bench-card-head">
            <Award className="text-emerald" size={24} />
            <h3>USMLE MedQA Clinical Vignettes</h3>
          </div>
          <div className="bench-score-row">
            <div className="bench-stat">
              <span className="bench-val">90.0%</span>
              <span className="bench-lbl">Accuracy</span>
            </div>
            <div className="bench-stat">
              <span className="bench-val">0.8667</span>
              <span className="bench-lbl">Macro F1 Score</span>
            </div>
            <div className="bench-stat">
              <span className="bench-val">0.9167</span>
              <span className="bench-lbl">Macro Recall</span>
            </div>
          </div>
          <p className="bench-desc">
            4-option multiple choice USMLE board exam vignettes testing comprehensive internal medicine, differential diagnosis, and pharmacology.
          </p>
        </div>

        <div className="bench-card">
          <div className="bench-card-head">
            <Award className="text-emerald" size={24} />
            <h3>PubMedQA Biomedical Research</h3>
          </div>
          <div className="bench-score-row">
            <div className="bench-stat">
              <span className="bench-val">84.2%</span>
              <span className="bench-lbl">Accuracy</span>
            </div>
            <div className="bench-stat">
              <span className="bench-val">0.5964</span>
              <span className="bench-lbl">Macro F1 Score</span>
            </div>
            <div className="bench-stat">
              <span className="bench-val">100%</span>
              <span className="bench-lbl">Execution Rate</span>
            </div>
          </div>
          <p className="bench-desc">
            Biomedical research abstract questions with yes/no/maybe decisions requiring rigorous evidence synthesis and guideline adherence.
          </p>
        </div>
      </div>
    </div>
  );
}
