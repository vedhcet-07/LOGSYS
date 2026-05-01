# Software Requirements Specification (SRS)
## Project Title
**LogMind: Multi-Modal Graph RAG Incident Assistant**

## 1. Purpose
This document specifies the complete functional and technical requirements for building a production-style **Multi-Modal Graph RAG system** for log analysis and incident debugging. The system must satisfy the course assignment requirements for a full-stack application, Dockerized deployment, multi-modal retrieval, vector database usage, LLM-based response generation, GitHub-based version control, and presentation readiness.

This SRS is intentionally written so it can be pasted into an AI coding assistant for implementation.

## 2. Assignment Alignment
The system must satisfy all required assignment components:

1. **Full-Stack Application**
   - Frontend: React (Vite preferred)
   - Backend: FastAPI (Python)

2. **Dockerization**
   - Frontend and backend each have separate Dockerfiles
   - Entire system runs with `docker-compose.yml`

3. **Multi-Modal Graph RAG**
   - Must support at least 3 modalities
   - Chosen modalities:
     - Text logs
     - Dashboard screenshots/images
     - Metrics files (CSV/JSON)
   - Pipeline must include:
     - Query processing
     - Embedding generation
     - Vector database retrieval
     - LLM response generation
   - Must include a knowledge graph layer

4. **Version Control**
   - Project hosted on GitHub
   - Meaningful commits
   - Branching strategy (feature branches + pull requests if possible)

5. **Presentation**
   - Must support a 10-minute presentation with:
     - System architecture
     - Live demo
     - Challenges faced
     - Literature survey on AI Agents / Agentic Workflows / MCP

6. **Evaluation Rubric Coverage**
   - System Design & Architecture
   - Multi-Modal Implementation
   - Functionality & Demo
   - Dockerization & Deployment
   - Code Quality & GitHub Usage
   - Literature Survey
   - Presentation Quality

## 3. Project Overview
The project is an intelligent incident assistant that analyzes logs, metrics, and dashboard screenshots to help identify system failures, explain likely causes, summarize anomalies, and produce a structured root cause analysis (RCA).

The system will implement **Graph RAG**, which combines:
- Vector similarity search over embedded multi-modal data
- Entity/relationship graph traversal using a knowledge graph
- LLM-based synthesis into grounded answers

The system should feel like an SRE/DevOps debugging assistant.

## 4. Problem Statement
Modern system failures produce signals across multiple sources:
- Application logs contain errors and stack traces
- Metrics reveal spikes in CPU, memory, latency, and error rate
- Dashboards visually show trends and anomalies

Traditional search or plain RAG does not connect these signals well. This project will build a multi-modal graph-based retrieval system that can correlate information from different sources and generate meaningful debugging assistance.

## 5. Users
### Primary Users
- Students demonstrating the assignment
- Developers debugging system issues
- Instructors evaluating the project

### User Goals
- Upload logs, screenshots, and metrics data
- Ask natural-language debugging questions
- Get anomaly summaries and RCA reports
- See evidence-backed explanations from retrieved context

## 6. Scope
### In Scope
- File upload for logs, screenshots, CSV/JSON metrics
- Multi-modal ingestion pipeline
- Embedding and vector storage in Pinecone
- Knowledge graph construction using NetworkX
- Retrieval + graph traversal + LLM synthesis
- Frontend interface for upload, querying, and results
- Dockerized frontend and backend
- Demo-ready output and simple graph visualization

### Out of Scope
- Real-time production log ingestion from live clusters
- Authentication and multi-user accounts
- Distributed tracing integrations
- Enterprise observability integrations
- Full-scale monitoring dashboards

## 7. Chosen Technical Stack
### Frontend
- React with Vite
- Tailwind CSS or simple CSS modules
- Axios/fetch for API calls
- Optional graph visualization with react-force-graph or vis-network

### Backend
- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- Python multipart file handling

### AI / Agentic Layer
- Google ADK for orchestrator and agents
- LiteLLM for multi-provider model routing
- Primary providers available through LiteLLM:
  - Gemini
  - Groq
  - OpenRouter
  - Ollama fallback

### Embeddings / Retrieval
- Pinecone as vector database
- Text embedding model via Gemini/OpenAI-compatible embedding endpoint or sentence-transformers fallback
- CLIP-like image embedding optional, but minimum requirement can be satisfied by converting screenshot understanding into text via Gemini Vision and embedding that text

### Knowledge Graph
- NetworkX

### Deployment
- Docker
- docker-compose

## 8. Multi-Modal Strategy
The system must support exactly these three modalities:

### Modality 1: Text Logs
Input examples:
- `.log`
- `.txt`
- structured application logs

Processing:
- Parse timestamps, level, service, message, error code
- Chunk long logs into windows
- Extract entities like service names, databases, endpoints, HTTP status codes, exceptions
- Generate embeddings for log chunks
- Store embeddings + metadata in Pinecone

### Modality 2: Dashboard Screenshots / Images
Input examples:
- `.png`
- `.jpg`
- screenshots of Grafana / Kibana / monitoring charts

Processing:
- Use Gemini Vision to describe chart anomalies and extract visible metrics/trends into structured text
- Example extracted text: “CPU spiked to 95%, error rate increased after 02:31, latency rose sharply in auth-service”
- Embed the generated textual summary
- Store in Pinecone with modality metadata = image

### Modality 3: Metrics Files
Input examples:
- `.csv`
- `.json`

Processing:
- Parse time-series metrics for CPU, memory, latency, error rate, requests, etc.
- Detect spikes, threshold violations, and trend breaks
- Convert structured metrics into text summaries and/or chunked JSON records
- Embed summaries and store in Pinecone
- Also create graph entities from services and anomalies

## 9. System Objectives
The system must be able to:
1. Ingest and index data from 3 modalities
2. Build a knowledge graph from entities and relationships in the ingested content
3. Accept natural-language queries about incidents
4. Retrieve relevant multi-modal evidence from Pinecone
5. Expand retrieval with graph traversal using NetworkX
6. Generate a grounded final answer using an LLM
7. Return outputs such as:
   - RCA report
   - incident timeline
   - affected services
   - anomaly summary
   - recommended next steps

## 10. Core Use Cases
### Use Case 1: Root Cause Analysis
User uploads logs, metrics, and dashboard screenshot, then asks:
- “Why did auth-service fail around 2:34 AM?”
Expected output:
- likely root cause
- evidence from logs
- correlated metric spike
- impacted downstream services

### Use Case 2: Error Summarization
User uploads a large log file and asks:
- “Summarize the main errors and anomalies.”
Expected output:
- grouped error types
- top recurring failures
- severity overview

### Use Case 3: Multi-Modal Correlation
User uploads a dashboard screenshot and metrics JSON with logs and asks:
- “Is the latency spike related to the DB timeout?”
Expected output:
- cross-modal evidence-backed answer

## 11. Functional Requirements
### FR-1 File Upload
The frontend must allow uploading one or more files from these modalities:
- Logs
- Images/screenshots
- CSV/JSON metrics

### FR-2 Ingestion Trigger
The backend must expose an ingestion endpoint that receives uploaded files and runs the ingestion pipeline.

### FR-3 Log Parsing
The system must parse logs into structured chunks with metadata fields such as:
- timestamp
- severity
- service
- message
- exception
- source file name

### FR-4 Image Understanding
The system must process dashboard screenshots with a multimodal model and extract meaningful textual observations.

### FR-5 Metrics Parsing
The system must parse CSV/JSON metrics and create structured summaries of anomalies and trend changes.

### FR-6 Embedding Generation
The system must generate embeddings for all ingestible content, either directly or after converting it into text.

### FR-7 Vector Storage
The system must store embeddings in Pinecone with metadata that includes:
- modality
- source file name
- timestamp or time window
- service name if detected
- chunk id

### FR-8 Knowledge Graph Construction
The system must build a NetworkX graph with:
- nodes for services, errors, incidents, metrics, and key entities
- edges for relationships like causes, affects, depends_on, observed_in, co_occurs_with

### FR-9 Query Input
The frontend must allow natural-language questions.

### FR-10 Query Processing
The backend must normalize the query, detect entities, and optionally perform query expansion.

### FR-11 Retrieval
The system must retrieve top-K relevant chunks from Pinecone using vector search.

### FR-12 Graph Traversal
The system must traverse the NetworkX graph from retrieved entities to find connected evidence.

### FR-13 Context Fusion
The system must combine retrieved vector results and graph-based evidence into a single grounded context package.

### FR-14 LLM Response Generation
The system must use an LLM to generate grounded responses such as:
- RCA
- summaries
- debugging insights
- recommended steps

### FR-15 Response Visualization
The frontend must display:
- answer text
- evidence snippets
- uploaded file names
- optionally graph view and agent trace

### FR-16 Agentic Orchestration
The system must use multiple agents coordinated by Google ADK.

### FR-17 Traceability
The system should display which agent handled which stage to strengthen the presentation demo.

## 12. Agent Architecture Requirements
The project must implement these agents:

### 12.1 Orchestrator Agent
Responsibilities:
- Receives user query
- Determines which tools/agents to call
- Coordinates retrieval and response generation
- Returns final structured output

### 12.2 Ingestion Agent
Responsibilities:
- Detects file modality
- Parses logs
- Analyzes images via Gemini Vision
- Parses metrics CSV/JSON
- Generates embeddings
- Stores content in Pinecone
- Updates the knowledge graph

### 12.3 Retrieval Agent
Responsibilities:
- Embeds the user query
- Queries Pinecone for top-K matches
- Extracts graph seed entities
- Traverses NetworkX graph
- Returns ranked evidence set

### 12.4 RCA Agent
Responsibilities:
- Takes fused evidence
- Produces RCA summary
- Produces error summary, incident timeline, and recommendations
- Outputs a structured JSON response for frontend rendering

## 13. Non-Functional Requirements
### NFR-1 Demo Reliability
The system must work in a demo setting using synthetic or preloaded data.

### NFR-2 Performance
For small demo datasets, response time should ideally be under 10 seconds for a query.

### NFR-3 Usability
The UI should be simple and presentation-ready.

### NFR-4 Modularity
Each backend concern should be isolated into tools/services for maintainability.

### NFR-5 Extensibility
Future modalities should be easy to add.

### NFR-6 Explainability
The system should provide evidence snippets and graph relationships to explain why an answer was generated.

### NFR-7 Portability
The full system must run with Docker.

## 14. API Requirements
### POST /api/ingest
Accepts multipart file upload.

Request:
- multiple files

Response:
```json
{
  "status": "success",
  "files_processed": 3,
  "chunks_indexed": 42,
  "graph_nodes": 18,
  "graph_edges": 27
}
```

### POST /api/query
Accepts user query.

Request:
```json
{
  "query": "Why did auth-service fail at 2:34 AM?"
}
```

Response:
```json
{
  "answer": "...",
  "root_cause": "Database timeout in user-db propagated to auth-service.",
  "evidence": [
    {"type": "log", "source": "app.log", "snippet": "..."},
    {"type": "metrics", "source": "metrics.json", "snippet": "..."},
    {"type": "image", "source": "dashboard.png", "snippet": "..."}
  ],
  "timeline": ["02:31 CPU spike", "02:33 DB timeout", "02:34 auth-service errors"],
  "recommendations": ["Increase DB connection pool", "Add retry with circuit breaker"]
}
```

### GET /api/graph
Returns graph JSON for visualization.

### GET /api/health
Returns service status.

## 15. Frontend Requirements
The frontend must include these pages/components:

### 15.1 Upload Panel
- Drag-and-drop or file picker
- Support logs, images, CSV, JSON
- Show uploaded files list
- Trigger ingest action

### 15.2 Query Panel
- Text input for user question
- Submit button
- Loading state while agents run

### 15.3 Results Panel
Must render:
- final answer
- root cause
- evidence cards
- recommendations
- timeline

### 15.4 Optional Enhancements
- graph visualization
- agent trace timeline
- modality badges
- source highlighting

## 16. Backend Module Requirements
### 16.1 log_parser.py
Must:
- parse common log formats
- split logs into chunks
- extract metadata and entities

### 16.2 image_analyzer.py
Must:
- call Gemini Vision on dashboard screenshots
- return structured anomaly summary text

### 16.3 metrics_parser.py
Must:
- load CSV/JSON
- compute anomalies such as spikes and threshold breaches
- convert them into text summaries

### 16.4 embedder.py
Must:
- expose a single embedding interface
- support provider fallback if needed

### 16.5 pinecone_store.py
Must:
- initialize Pinecone index
- upsert vectors
- query by embedding

### 16.6 graph_store.py
Must:
- create and update NetworkX graph
- save graph to file if needed
- perform traversal for related entities

### 16.7 rca_generator.py or rca_agent.py
Must:
- accept fused context
- call LLM
- return structured RCA output

## 17. Retrieval Pipeline Requirements
The backend query pipeline must follow this sequence:
1. Receive user query
2. Normalize and optionally expand query
3. Generate query embedding
4. Query Pinecone top-K
5. Extract entities from top results and query
6. Traverse NetworkX graph for linked evidence
7. Merge and rerank evidence
8. Build final prompt with context
9. Generate answer using LLM
10. Return structured JSON response

## 18. Graph Schema
### Node Types
- service
- error
- metric
- incident
- file
- endpoint
- database
- screenshot_summary

### Edge Types
- causes
- affects
- depends_on
- observed_in
- spikes_before
- co_occurs_with
- triggered_by

## 19. Prompting Requirements
The final LLM prompt for RCA must instruct the model to:
- answer only from retrieved context
- identify the likely root cause
- mention uncertainty when evidence is incomplete
- provide timeline of events
- provide actionable recommendations
- cite which modality each point came from where possible

Example output format:
```json
{
  "root_cause": "...",
  "summary": "...",
  "timeline": ["..."],
  "affected_services": ["..."],
  "recommendations": ["..."],
  "confidence": "high|medium|low"
}
```

## 20. Data Requirements
The project may use synthetic data for flexibility.
Required demo data should include:
- one realistic log file with cascading failures
- one metrics JSON or CSV showing anomaly spikes
- one dashboard screenshot that visually reflects the anomaly

Recommended scenario:
- database latency spike
- increased API response time
- auth-service timeout failures
- elevated 5xx errors

## 21. Demo Requirements
The live demo must show:
1. System architecture slide
2. Upload of three modalities
3. Successful ingestion confirmation
4. A natural-language query
5. Multi-modal evidence retrieval
6. RCA output
7. Optional graph visualization and agent trace

## 22. Docker Requirements
The solution must include:
- `frontend/Dockerfile`
- `backend/Dockerfile`
- root `docker-compose.yml`

### Docker Compose Must Start
- frontend service
- backend service

Optional:
- ollama service

### Environment Variables
Must support:
- GEMINI_API_KEY
- GROQ_API_KEY
- OPENROUTER_API_KEY
- PINECONE_API_KEY
- PINECONE_INDEX_NAME
- OLLAMA_BASE_URL

## 23. GitHub Requirements
Repository must include:
- meaningful commit history
- README.md with setup and run steps
- architecture diagram image
- screenshots or demo GIF if possible
- branch names like `feature/backend-ingestion`, `feature/frontend-ui`

Commit examples:
- `feat: add Pinecone ingestion pipeline for log chunks`
- `feat: implement Gemini screenshot analysis tool`
- `feat: build RCA response panel in frontend`
- `chore: add docker-compose for frontend and backend`

## 24. Code Quality Requirements
- Clean folder structure
- Small focused modules
- Use environment variables, not hardcoded API keys
- Add basic error handling
- Add logging in backend
- Type hints where possible
- Keep prompts in separate constants/functions where possible

## 25. Suggested Folder Structure
```text
project-root/
  frontend/
    src/
      components/
      pages/
      services/
    Dockerfile
    package.json
  backend/
    agents/
    tools/
    services/
    api/
    data/
    main.py
    requirements.txt
    Dockerfile
  docker-compose.yml
  .env.example
  README.md
```

## 26. Success Criteria
The project is considered successful if:
- it supports 3 modalities
- it uses Graph RAG with a vector DB and a graph layer
- it produces meaningful incident analysis answers
- it runs through Docker Compose
- it is hosted on GitHub
- it is presentable in 10 minutes

## 27. Mapping to Evaluation Rubric
### 27.1 System Design & Architecture (4 marks)
Covered by:
- full-stack architecture
- modular backend
- Graph RAG pipeline
- agent orchestration design

### 27.2 Multi-Modal Implementation (5 marks)
Covered by:
- logs
- screenshots/images
- metrics CSV/JSON
- cross-modal retrieval and synthesis

### 27.3 Functionality & Demo (4 marks)
Covered by:
- working upload flow
- query flow
- meaningful RCA and summaries
- visible evidence-backed outputs

### 27.4 Dockerization & Deployment (2 marks)
Covered by:
- frontend Dockerfile
- backend Dockerfile
- docker-compose orchestration

### 27.5 Code Quality & GitHub Usage (2 marks)
Covered by:
- modular code structure
- README
- meaningful commits
- documented setup

### 27.6 Literature Survey (2 marks)
Covered externally in presentation using one paper on AI Agents / Agentic Workflows / MCP.
Recommended paper: ReAct.

### 27.7 Presentation Quality (1 mark)
Covered by:
- clean UI
- structured explanation
- architecture diagram
- concise demo flow

## 28. Implementation Priorities
### Must Have
- file upload
- 3-modality ingestion
- Pinecone indexing
- NetworkX graph build
- query → retrieve → generate flow
- RCA output
- Docker setup

### Good to Have
- graph visualization
- agent trace UI
- reranking
- provider fallback selection UI

### Nice to Have
- export RCA as markdown/pdf
- confidence score visualization
- incident comparison view

## 29. Risks and Mitigations
### Risk: Vision extraction inconsistent
Mitigation: use screenshots with simple clear charts and labels; cache extracted text.

### Risk: Pinecone setup delay
Mitigation: create index early; keep local in-memory fallback for testing.

### Risk: Multi-agent complexity
Mitigation: keep agents thin and delegate heavy work to tools.

### Risk: Docker issues
Mitigation: keep containers simple; use a single backend image and simple frontend static build.

### Risk: Time constraint
Mitigation: prioritize core demo flow over polish.

## 30. Final Instruction for AI Coding Assistant
Build the project exactly according to this SRS. Prioritize a working end-to-end demo over overengineering. Ensure that all assignment requirements are visibly satisfied in both implementation and demo flow. Generate modular production-style code with clear folder separation, Docker support, and a presentation-friendly UI.
