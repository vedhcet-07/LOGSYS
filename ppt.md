# LogMind — PPT Slide Content
### Multi-Modal Graph RAG Incident Assistant

---

## SLIDE 1 — Title Slide

**Heading:** LogMind
**Subheading:** Multi-Modal Graph RAG Incident Assistant

**Tagline:** *"From logs to root cause — in seconds."*

**Team:** [Your Team Names]
**Course / Submission:** Multi-Modal RAG System — May 2, 2026

---

## SLIDE 2 — Problem Statement

**Heading:** The Problem with Incident Debugging Today

**Bullets:**
- 🔴 **Scattered signals** — logs in one place, metrics in another, dashboards nowhere near the error
- 🔴 **Manual correlation** — engineers grep through thousands of log lines manually
- 🔴 **Context loss** — no link between an error in the log and the service it belongs to
- 🔴 **Slow MTTR** — Mean Time To Resolve incidents averages **4.5 hours** in production systems
- 🔴 **Visual data ignored** — Grafana/Prometheus screenshots contain rich information that text-only tools miss

**Bottom callout:**
> *"Engineers spend more time finding the problem than fixing it."*

---

## SLIDE 3 — Solution Overview

**Heading:** Meet LogMind

**One-liner:**
> An AI-powered incident assistant that reads logs, metrics, and dashboard screenshots together — and tells you exactly what went wrong and why.

**Three columns:**

| 📥 Ingest | 🧠 Analyse | 📤 Respond |
|---|---|---|
| Upload logs, CSV metrics, Grafana PNGs | Multi-modal embedding + Knowledge Graph | Root Cause Analysis with evidence, timeline, and recommendations |

**Key differentiator callout:**
> Not just vector search — **Graph RAG** connects services, errors, and files into a relational knowledge graph for multi-hop reasoning.

---

## SLIDE 4 — Tech Stack

**Heading:** Technology Stack

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND          React + Vite · react-force-graph │
│  BACKEND           FastAPI (Python)                 │
│  LLM               Groq — llama-3.3-70b-versatile  │
│  VISION            Gemini 2.0 Flash (multi-modal)   │
│  EMBEDDINGS        Gemini text-embedding-005 (768d) │
│  VECTOR DB         Pinecone (serverless namespaces) │
│  KNOWLEDGE GRAPH   NetworkX DiGraph                 │
│  INFRA             Docker + docker-compose          │
└─────────────────────────────────────────────────────┘
```

**Why these tools:**
- Groq → zero-cost, 500 tok/s — real-time RCA without latency
- Gemini Vision → only model that can read Grafana screenshots natively
- Pinecone namespaces → session-level data isolation out of the box

---

## SLIDE 5 — System Architecture

**Heading:** End-to-End Pipeline

```
User Uploads Files
       │
       ▼
┌──────────────────┐
│  Ingestion Layer │  log_parser · image_analyzer · metrics_parser
│  (3 Modalities)  │
└────────┬─────────┘
         │  Chunks + Metadata
         ▼
┌─────────────────────────────────────┐
│         Embedding Engine            │  Gemini text-embedding-005
│  768-dim vectors per chunk          │  Output dim: 768 (Matryoshka)
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
Pinecone      NetworkX
(per-session  (Knowledge
 namespace)    Graph)
    │             │
    └──────┬──────┘
           │
           ▼
┌──────────────────┐
│  Retrieval Agent │  Vector search + Graph traversal (2-hop)
│                  │  Entity extraction → neighbour lookup
└────────┬─────────┘
         │  Evidence + Graph context
         ▼
┌──────────────────┐
│    RCA Agent     │  Groq llama-3.3-70b
│                  │  Structured RCAOutput: root_cause, timeline,
│                  │  affected_services, recommendations, confidence
└────────┬─────────┘
         │
         ▼
   Chat UI Response
   + Evidence Tab + Timeline Tab + Graph Tab + Trace Tab
```

**Speaker note:** Walk the diagram left-to-right once, point to each box, then say: *"Every component is isolated per session — Session A's logs never touch Session B's graph."*

---

## SLIDE 6 — Multi-Modal Implementation

**Heading:** How Each Modality Is Processed

**Three columns:**

### 📄 Text Logs (.log / .txt)
- Windowed chunking (50 lines, 10-line overlap)
- Entity extraction: services, exceptions, databases, IPs
- Parsed into `BaseChunk` → embedded → stored in Pinecone
- Graph edges: `file → service`, `exception → file`

### 📊 Metrics (.csv / .json)
- Statistical analysis: mean, std-dev, P95, P99
- Anomaly detection: values > 2σ flagged automatically
- Spike detection with timestamps preserved
- Compatible with Prometheus export format

### 🖼️ Dashboard Screenshots (.png / .jpg)
- Sent directly to **Gemini 2.0 Flash** Vision API
- Extracts: error rates, latency spikes, service names, anomalous trends
- Returns structured text summary → embedded like any other chunk
- Works on Grafana, Kibana, custom dashboards

**Graph RAG advantage:**
> Plain RAG returns top-K chunks. **Graph RAG** asks: *"What else is connected to the services mentioned in those chunks?"* — exposing hidden cascading failures plain vector search misses.

---

## SLIDE 7 — Agent Design

**Heading:** Agentic Pipeline — 3 Agents + 1 Orchestrator

```
                  Orchestrator
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
  Retrieval Agent            RCA Agent
  ─────────────────          ──────────────────
  1. Embed query             1. Build LLM prompt
  2. Pinecone search            (evidence + graph)
     (session namespace)     2. Call Groq LLM
  3. Entity extraction       3. Parse structured
  4. Graph traversal            RCAOutput
  5. Return evidence         4. Return with
     + graph nodes              confidence score
```

**Each agent is:**
- Independently testable
- Has its own trace log visible in the UI Trace tab
- Stateless — state lives in session_store, not the agent

**Orchestrator role:** Sequences agents, merges traces, assembles the final response.

---

## SLIDE 8 — Live Demo

**Heading:** Live Demo

**Script (what to show, in order):**

1. **Terminal** — `docker-compose up` running both containers (30 sec)
2. **UI** — Open `http://localhost:3000`, show 3-column layout
3. **New Session** — Click "+ New", show session created in sidebar
4. **Upload** — Drag `demo_app.log` + `demo_metrics.json` + `dashboard.png` into session
5. **Ingest** — Click Ingest, watch "8 nodes, 6 edges" appear
6. **Query** — Type: *"Why did auth-service fail at 2:31 AM?"*
7. **Response** — Show: root cause card, confidence badge, recommendations
8. **Evidence tab** — Show 4 evidence items with relevance scores
9. **Timeline tab** — Show colored event sequence
10. **Graph tab** — Click `auth-service` node → show detail panel
11. **Trace tab** — Walk through 9 agent trace steps

**Talking point during demo:**
> *"Notice Session B here has zero knowledge of Session A's data — complete isolation. This matters in real ops teams where multiple incidents are investigated simultaneously."*

---

## SLIDE 9 — GitHub & Code Quality

**Heading:** Version Control & Project Structure

**Repo:** `github.com/[YOUR_USERNAME]/logmind`

**Folder structure:**
```
logmind/
├── backend/
│   ├── agents/          # retrieval_agent, rca_agent, orchestrator
│   ├── services/        # embedder, graph_store, pinecone_store, session_store
│   ├── api/routes.py    # 9 session endpoints + 3 global endpoints
│   ├── models.py        # Pydantic schemas
│   └── Dockerfile
├── frontend/
│   ├── src/components/  # ChatWindow, LeftSidebar, RightSidebar, ChatMessage
│   ├── src/services/    # api.js (all 15 API calls)
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

**Metrics:**
- 15+ API endpoints documented via Swagger at `/docs`
- Phase-wise test files: `test_phase4a.py` (25 checks), `test_phase4b.py` (35 checks)
- Zero hardcoded secrets — all via `.env`

---

## SLIDE 10 — Literature Survey

**Heading:** Research Foundation

**Paper 1 — ReAct: Synergizing Reasoning and Acting in Language Models**
*Yao et al., 2022 — Google Brain*
- **Problem:** LLMs hallucinate when answering factual questions without grounding
- **Method:** Interleave reasoning traces with external tool calls (Retrieve → Think → Act loop)
- **Our mapping:** Retrieval Agent implements the Retrieve step; RCA Agent implements the Think+Act step; agent traces in the UI expose the reasoning chain

**Paper 2 — From Local to Global: A Graph RAG Approach**
*Edge et al., 2024 — Microsoft Research*
- **Problem:** Standard vector RAG fails on queries requiring cross-document reasoning
- **Method:** Build a knowledge graph from entities/relationships, traverse at query time
- **Our mapping:** `graph_store.py` builds the entity graph during ingestion; `get_neighbors()` performs 2-hop traversal at query time

**Key insight from literature:**
> *"Graph traversal surfaces relationships that cosine similarity alone cannot — exactly what cascading failure analysis requires."*

---

## SLIDE 11 — Challenges Faced

**Heading:** Challenges & How We Solved Them

| Challenge | What Happened | Solution |
|---|---|---|
| **Quota exhaustion on Gemini** | `429 RESOURCE_EXHAUSTED` on text generation after ~10 queries | Decoupled text LLM (Groq, free tier) from vision (Gemini only) |
| **SDK breaking change** | `google-generativeai` deprecated mid-build | Migrated all code to `google-genai` SDK with new client interface |
| **Cross-session contamination** | All sessions shared one graph — queries leaked between incidents | Implemented per-session Pinecone namespaces + isolated NetworkX graphs |
| **Embedding dimension mismatch** | Pinecone index dim=768, model default=3072 | Used Matryoshka truncation: `output_dimensionality=768` |
| **Vision model instability** | Gemini returned different schema across calls | Added structured prompt with explicit JSON output format |
| **Time constraint** | Full stack + agents + UI in one sprint | Phase-wise build plan (4A→4B→4C→4D) — backend before UI, tests before features |

---

## SLIDE 12 — Thank You

**Heading:** Thank You

**Tagline:** *"LogMind — because your logs shouldn't be a mystery."*

```
🔗 GitHub:     github.com/[YOUR_USERNAME]/logmind
📦 Run Locally: docker-compose up
📖 API Docs:   http://localhost:8000/docs
```

**Team:**
- [Name 1]
- [Name 2]
- [Name 3]

> *Open for questions.*