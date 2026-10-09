# ── Stage 1: Build the React Frontend ─────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/client

# Copy package definitions and install dependencies
COPY medihive-frontend/client/package*.json ./
RUN npm ci

# Copy client source files and build production static bundle
COPY medihive-frontend/client/ ./
RUN npm run build

# ── Stage 2: Python Backend with FastAPI & ChromaDB ──────────
FROM python:3.11-slim

# System dependencies for PyMuPDF and SQLite build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs as user with UID 1000
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python requirements
COPY MediHive/requirements.txt MediHive/requirements_rag_addon.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_rag_addon.txt

# Copy Backend codebase
COPY MediHive/ /app/

# Copy the built React app from Stage 1 into /app/static_react
COPY --from=frontend-builder /build/client/dist /app/static_react

# Ensure the data directory exists and set permissions for user 1000
RUN mkdir -p /app/data /app/data/chroma_db /home/user/.cache && \
    chown -R user:user /app /home/user

# Switch to non-root user (Hugging Face default)
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PORT=7860

# Pre-download the Hugging Face embedding model during docker build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Hugging Face Spaces standard port is 7860
EXPOSE 7860

# Launch FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
