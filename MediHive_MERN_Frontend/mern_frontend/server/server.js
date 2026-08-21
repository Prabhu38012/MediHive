/**
 * server/server.js
 *
 * Express proxy server sitting between the React frontend and the
 * Python FastAPI MediHive backend (agents, RAG, fusion all live there
 * and are UNCHANGED - this server does not reimplement any of that
 * logic, it just forwards requests).
 *
 * Why a proxy at all instead of React calling FastAPI directly:
 *   - Keeps the FastAPI URL/port out of client-side code
 *   - One place to add auth, rate limiting, logging, or caching later
 *   - Matches the requested MERN-style architecture (React -> Express -> ...)
 *
 * Run with:
 *   npm install
 *   npm start
 *
 * Requires the Python server already running separately:
 *   python -m uvicorn app:app --reload   (in the MediHive Python project)
 */

import express from "express";
import cors from "cors";
import axios from "axios";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;
const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

app.use(cors());
app.use(express.json());

// Requests to the 5-agent pipeline can legitimately take several
// minutes on local LLM inference - don't let axios time out early.
const PYTHON_REQUEST_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

/**
 * Health check for the Node layer itself, and a quick check that it
 * can actually reach the Python backend.
 */
app.get("/api/health", async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/`, { timeout: 5000 });
    res.json({
      node_server: "ok",
      python_backend: "reachable",
      python_status: response.data,
    });
  } catch (err) {
    res.status(502).json({
      node_server: "ok",
      python_backend: "unreachable",
      error: err.message,
      hint: "Is the Python server running? (python -m uvicorn app:app --reload)",
    });
  }
});

/**
 * Knowledge base status - how many RAG chunks are indexed.
 */
app.get("/api/knowledge-base/status", async (req, res) => {
  try {
    const response = await axios.get(`${PYTHON_API_URL}/knowledge-base/status`, {
      timeout: 10000,
    });
    res.json(response.data);
  } catch (err) {
    res.status(502).json({
      error: "Could not reach Python backend",
      details: err.message,
    });
  }
});

/**
 * Main ask endpoint - forwards the question to the Python /ask
 * endpoint, which runs the 5 agents, RAG retrieval, debate, and
 * iterative fusion, then returns the full response untouched.
 */
app.post("/api/ask", async (req, res) => {
  const { question } = req.body;

  if (!question || typeof question !== "string" || !question.trim()) {
    return res.status(400).json({ error: "A non-empty 'question' string is required." });
  }

  try {
    const response = await axios.post(
      `${PYTHON_API_URL}/ask`,
      { question },
      { timeout: PYTHON_REQUEST_TIMEOUT_MS }
    );
    res.json(response.data);
  } catch (err) {
    if (err.response) {
      // Python backend responded with an error status - forward its detail
      res.status(err.response.status).json({
        error: "Python backend returned an error",
        details: err.response.data,
      });
    } else {
      res.status(502).json({
        error: "Could not reach Python backend",
        details: err.message,
        hint: "Is the Python server running? (python -m uvicorn app:app --reload)",
      });
    }
  }
});

/**
 * Shared memory lookup for a given session - passthrough to Python.
 */
app.get("/api/memory/:sessionId", async (req, res) => {
  try {
    const response = await axios.get(
      `${PYTHON_API_URL}/memory/${req.params.sessionId}`,
      { timeout: 10000 }
    );
    res.json(response.data);
  } catch (err) {
    res.status(502).json({
      error: "Could not reach Python backend",
      details: err.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`MediHive Express proxy server running on http://localhost:${PORT}`);
  console.log(`Forwarding to Python backend at ${PYTHON_API_URL}`);
});
