# LogMind — Multi-Modal Graph RAG Incident Assistant

> Upload logs, metrics, and dashboard screenshots. Ask natural-language questions. Get AI-powered root cause analysis backed by multi-modal evidence.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React Frontend (Vite)                                          │
│  Upload Panel │ Query Panel │ Results Panel │ Graph Panel       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP /api/*
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI Backend                                                 │
│  ┌─────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │  Ingestion  │  │   Retrieval    │  │     RCA Agent       │  │
│  │   Agent     │  │    Agent       │  │  (LlmAgent + ADK)   │  │
│  └──────┬──────┘  └───────┬────────┘  └──────────┬──────────┘  │
│         │                 │                       │              │
│  ┌──────▼──────────────────▼───────────────────────▼──────────┐ │
│  │               Orchestrator Agent (ADK)                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Services:  log_parser │ image_analyzer │ metrics_parser        │
│             embedder   │ pinecone_store │ graph_store           │
└──────────────────────────────────────────────────────────────────┘
         │ embed + upsert                │ NetworkX DiGraph
┌────────▼────────┐             ┌────────▼────────────────────────┐
│  Pinecone (v3)  │             │  graph.gpickle (persisted)      │
│  Vector Search  │             │  NetworkX Knowledge Graph       │
└─────────────────┘             └─────────────────────────────────┘
```

---

## Quick Start — Docker (Recommended)

```bash
# 1. Clone
git clone https://github.com/<your-org>/logmind.git
cd logmind

# 2. Configure
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY, PINECONE_API_KEY, etc.

# 3. Run
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## Manual Dev Setup

### Backend

```bash
cd backend

# Windows PowerShell
python -m venv ..\.venv
..\.venv\Scripts\pip install -r requirements.txt

# Copy and fill in your API keys
cp ../.env.example ../.env

# Start (PowerShell)
$env:PYTHONPATH = $PWD; ..\.venv\Scripts\uvicorn main:app --port 8000 --reload
# OR use the --app-dir flag:
..\.venv\Scripts\uvicorn main:app --app-dir . --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
# Vite proxies /api → http://localhost:8000 automatically
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Liveness probe |
| `POST` | `/api/ingest` | Upload files (multipart) for ingestion |
| `POST` | `/api/query`  | Submit natural-language incident question |
| `GET`  | `/api/graph`  | Get knowledge graph JSON for visualization |

Full interactive docs: `http://localhost:8000/docs`

---

## Supported Modalities

| Modality | Formats | Processing |
|----------|---------|------------|
| **Text Logs** | `.log`, `.txt` | Parsed → chunked → embedded → Pinecone |
| **Metrics** | `.csv`, `.json` | Spike detection → text summary → embedded |
| **Dashboard Screenshots** | `.png`, `.jpg` | Gemini Vision → text summary → embedded |

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Required keys:

- `GEMINI_API_KEY` — for LLM + Vision + embeddings
- `PINECONE_API_KEY` — vector database
- `PINECONE_INDEX_NAME` — defaults to `logmind-index`

---

## Project Structure

```
logmind/
├── frontend/           React + Vite UI
├── backend/
│   ├── agents/         ADK agent implementations
│   ├── tools/          Agent tool functions
│   ├── services/       Core services (parsers, embedder, stores)
│   ├── api/            FastAPI routes
│   ├── data/demo/      Pre-baked synthetic demo files
│   └── main.py         App entry point
├── docker-compose.yml
├── .env.example
└── LITERATURE.md       Literature survey references
```

---

## Literature Survey

See [LITERATURE.md](LITERATURE.md) for references on:
- Graph RAG
- Agentic Workflows (ReAct)
- Multi-Modal Retrieval
- MCP (Model Context Protocol)
