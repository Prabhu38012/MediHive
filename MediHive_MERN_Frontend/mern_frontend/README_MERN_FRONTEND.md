# MedTrustAI — React + Express Frontend (MERN-style)

Architecture:
```
React (client, port 3000)
        │  fetch("/api/...")
        ▼
Express (server, port 5000)
        │  axios -> forwards request
        ▼
Python FastAPI (your existing MedTrustAI backend, port 8000)
        │
        ▼
Agents + RAG + Debate + Iterative Fusion  (UNCHANGED - all Python)
```

The **M** (MongoDB) isn't used here — you chose the Express-proxy option,
which doesn't need a database of its own. Your Python backend's SQLite
shared memory (`memory/shared_memory.py`) still handles all persistence.
If you want Express/MongoDB to separately log chat history later, say so
and I'll add it — it wasn't part of what you asked for this round.

Your Python backend (agents, RAG pipeline, debate, iterative fusion) is
**completely unchanged** — Express only forwards requests to it and
relays the response back. All the AI logic still lives in Python.

---

## Folder structure

```
medihive-frontend/
├── server/                 <- Express (Node) proxy
│   ├── package.json
│   ├── server.js
│   └── .env.example
│
└── client/                 <- React (Vite)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        └── index.css
```

---

## Setup

You'll run **three** things at once, each in its own terminal:
1. Python FastAPI backend (your existing MedTrustAI project)
2. Express server (new)
3. React dev server (new)

### 1. Python backend (unchanged — you already have this running)
```powershell
cd MediHive
python -m uvicorn app:app --reload
```
Leave this running. Confirm it works: `http://127.0.0.1:8000/`

### 2. Express server
```powershell
cd medihive-frontend/server
npm install
copy .env.example .env
npm start
```
You should see:
```
MedTrustAI Express proxy server running on http://localhost:5000
Forwarding to Python backend at http://127.0.0.1:8000
```

Quick check it can reach Python:
```
http://localhost:5000/api/health
```
Should show `"python_backend": "reachable"`.

### 3. React frontend
Open a **third terminal**:
```powershell
cd medihive-frontend/client
npm install
npm run dev
```
You should see something like:
```
VITE v5.4.x  ready in 400 ms
➜  Local:   http://localhost:3000/
```

Open that URL in your browser.

---

## How requests flow

1. You type a question in React and click "Ask MedTrustAI"
2. React sends `POST /api/ask` to Express (same-origin thanks to Vite's
   dev proxy config in `vite.config.js` — no CORS setup needed)
3. Express forwards it to `POST http://127.0.0.1:8000/ask` on your
   Python backend
4. Python runs the full pipeline (RAG retrieval → 5 agents → debate →
   iterative fusion) and returns the response
5. Express relays that response straight back to React
6. React renders: consensus answer, badges (debate/RAG/confidence),
   retrieved sources, and every agent's answer + fusion weight with a
   visual bar

Same visual design and information as the earlier static HTML version —
just now properly split into a React component structure with an
Express layer in front, matching the MERN-style architecture you asked for.

---

## Important — timing is unchanged

Local LLM inference through 5 agents still takes 1-3+ minutes per
question. The Express server's proxy timeout is set to 15 minutes to
accommodate this (`PYTHON_REQUEST_TIMEOUT_MS` in `server.js`) — don't
lower it unless your machine is fast enough that it's unnecessary.

---

## Building for production (optional, for final submission)

```powershell
cd medihive-frontend/client
npm run build
```
This creates a `dist/` folder with static files. You could serve these
directly from Express instead of running two dev servers — ask if you
want that wired up for your final submission.

---

## Troubleshooting

**React shows "Could not reach server" / health check fails:**
- Confirm Python is running on port 8000
- Confirm Express is running on port 5000 (`npm start` in `server/`)
- Check `server/.env` has the right `PYTHON_API_URL`

**"Cannot find module" errors:**
- Run `npm install` again in whichever folder (`server/` or `client/`)
  is missing dependencies — `node_modules/` isn't included in this zip,
  you need to install fresh on your machine
