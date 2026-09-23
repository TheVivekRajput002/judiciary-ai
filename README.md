# LexiAI — Legal Research AI Agent

> Upload legal documents, ask research questions, and get structured, cited answers — powered by a multi-stage reasoning pipeline.

LexiAI is a **domain-specific AI research system** for legal professionals, researchers, and students. It is not a general-purpose chatbot. Every query passes through a full agentic pipeline, retrieves real evidence, and returns a grounded, cited answer — never a hallucinated one.

---

## Features

- **Document Ingestion & RAG** — Upload PDFs, DOCX, or TXT files; chunks are embedded with FastEmbed and stored in pgvector for semantic search
- **Legal Web Research** — Live search via Tavily, scoped to authoritative legal sources
- **Intelligent Routing** — Each query is auto-classified as `Document`, `Web`, or `Combined` before any retrieval happens
- **8-Stage Agent Pipeline** — Dedicated LangGraph nodes for Understand → Plan → Retrieve → Research → Reason → Synthesize → Cite → Remember
- **Session Memory** — Full conversation history persisted in PostgreSQL; pronoun and reference resolution across turns ("the second issue", "those judgments")
- **Conflict Detection** — Conflicting authorities are surfaced explicitly, never silently merged
- **Hallucination Guard** — Returns `insufficient_evidence` responses rather than fabricating citations
- **Streaming Responses** — Server-Sent Events (SSE) stream stage progress and answer tokens in real time
- **Interactive API Docs** — Auto-generated Swagger UI available in debug mode at `/docs`

---

## Tech Stack

| Layer                         | Technology                                        |
| ----------------------------- | ------------------------------------------------- |
| **Frontend**            | React 19, TypeScript, Vite, Tailwind CSS v4       |
| **Streaming UI**        | Vercel AI SDK (`@ai-sdk/react`)                 |
| **State Management**    | Zustand                                           |
| **Routing (FE)**        | React Router v7                                   |
| **Backend**             | FastAPI, Uvicorn, Python 3.11+                    |
| **Agent Orchestration** | LangGraph                                         |
| **LLM Provider**        | Groq (`langchain-groq`)                         |
| **Embeddings**          | FastEmbed (local ONNX)                            |
| **Database**            | PostgreSQL (Neon serverless) + SQLAlchemy (async) |
| **Vector Search**       | pgvector extension                                |
| **Migrations**          | Alembic                                           |
| **Document Parsing**    | PyPDF, python-docx                                |
| **Web Search**          | Tavily                                            |
| **Resilience**          | Tenacity (retry logic)                            |
| **Auth**                | None (session-based, no login required)           |
| **Hosting**             | Neon (DB)                                         |

---

## Quick Start

### Prerequisites

- Python **3.11+**
- Node.js **20+** and npm
- A PostgreSQL database with the **`pgvector` extension** enabled — [Neon](https://neon.tech) (free tier works)
- A **[Groq API key](https://console.groq.com)** (free tier available)
- A **[Tavily API key](https://tavily.com)** for web search
- *(Optional)* A **[VoyageAI API key](https://www.voyageai.com)** if you prefer Voyage embeddings over the default local FastEmbed

---

### Install

**Backend:**

```bash
# Clone the repo
git clone https://github.com/your-username/LexiAI.git
cd LexiAI/backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Frontend:**

```bash
cd ../frontend
npm install
```

---

### `.env` Setup

```bash
# Inside backend/
cp .env.example .env
```

Open `backend/.env` and fill in your values (see [Environment Variables](#environment-variables) below).

---

### Run

In **two separate terminals**:

```bash
# Terminal 1 — Backend (http://localhost:8000)
cd backend
source .venv/bin/activate
alembic upgrade head          # Run migrations (first time only)
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — Frontend (http://localhost:5173)
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser. The Swagger API docs are at **http://localhost:8000/docs** (debug mode only).

---

## Repository Structure

```
LexiAI/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── nodes/                  # One file per pipeline stage
│   │   │   │   ├── understand.py       # Intent classification + reference resolution
│   │   │   │   ├── plan.py             # Routing decision + retrieval plan
│   │   │   │   ├── retrieve.py         # pgvector semantic search
│   │   │   │   ├── research.py         # Tavily legal web search
│   │   │   │   ├── reason.py           # Evidence evaluation + conflict detection
│   │   │   │   ├── synthesize.py       # Structured answer drafting
│   │   │   │   ├── cite.py             # Inline citation attachment
│   │   │   │   ├── remember.py         # Session memory persistence
│   │   │   │   ├── clarify.py          # Ambiguous query handling
│   │   │   │   └── insufficient_evidence.py
│   │   │   ├── graph.py                # LangGraph graph definition
│   │   │   └── state.py                # Shared AgentState schema
│   │   ├── api/
│   │   │   ├── chat.py                 # POST /api/chat — SSE streaming
│   │   │   ├── documents.py            # Document upload + management
│   │   │   └── sessions.py             # Session CRUD
│   │   ├── core/                       # Config, logging, error helpers
│   │   ├── db/                         # SQLAlchemy models + async session
│   │   ├── llm/                        # LLM client wrapper
│   │   ├── memory/                     # Context loader + context writer
│   │   ├── rag/                        # Chunking, embedding, ingestion
│   │   ├── web_search/                 # Tavily query builder + client
│   │   └── main.py                     # FastAPI app entrypoint
│   ├── alembic/                        # DB migration scripts
│   │   └── versions/
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/                 # Shared UI components
│   │   ├── pages/
│   │   │   ├── IndexPage.tsx           # Session list / landing
│   │   │   └── SessionPage.tsx         # Main chat + document panel
│   │   ├── store/                      # Zustand state stores
│   │   ├── lib/                        # API client, utilities
│   │   └── types/                      # TypeScript type definitions
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── Context/                            # Project docs (PRD, tech spec, schema)
```

---

## Architecture Overview

```
┌─────────────────────────────────┐          ┌──────────────────────────────────────┐
│  FRONTEND  (Vite + React 19)    │          │  BACKEND  (FastAPI + Uvicorn)         │
│                                 │  HTTP /  │                                       │
│  @ai-sdk/react  ←  useChat()    │  SSE     │  LangGraph pipeline                  │
│  Zustand stores  (state only)   │ ◄──────► │  Understand → Plan → Retrieve         │
│  React Router   (navigation)    │          │  → Research → Reason → Synthesize     │
│                                 │          │  → Cite → Remember                    │
└─────────────────────────────────┘          │                                       │
                                              │  RAG  (pgvector semantic search)      │
                                              │  Web search  (Tavily)                 │
                                              │  Session memory  (PostgreSQL)         │
                                              └──────────────────┬────────────────────┘
                                                                 │
                                              ┌──────────────────▼────────────────────┐
                                              │  PostgreSQL on Neon  (serverless)      │
                                              │  ├── sessions, messages, documents     │
                                              │  ├── document_chunks  (text + metadata)│
                                              │  └── chunk_embeddings  (pgvector)      │
                                              └────────────────────────────────────────┘
```

**Key rule:** All LLM calls, tool invocations, retrieval, and agent orchestration run **server-side in FastAPI**. The frontend never contacts an LLM provider directly and never sees a provider API key. The Vercel AI SDK is used purely as a streaming UI convenience layer.

---

## API Endpoints

### Sessions

| Method     | Endpoint                                | Description                             |
| ---------- | --------------------------------------- | --------------------------------------- |
| `POST`   | `/api/sessions`                       | Create a new research session           |
| `GET`    | `/api/sessions`                       | List sessions (most recent 20)          |
| `GET`    | `/api/sessions/{session_id}`          | Get session detail with message history |
| `DELETE` | `/api/sessions/{session_id}/messages` | Clear all messages in a session         |

**Example — create session:**

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Contract Dispute Research"}'
```

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Contract Dispute Research",
  "created_at": "2026-09-24T01:00:00Z",
  "last_active_at": "2026-09-24T01:00:00Z"
}
```

---

### Documents

| Method     | Endpoint                           | Description                                                      |
| ---------- | ---------------------------------- | ---------------------------------------------------------------- |
| `POST`   | `/api/documents?session_id={id}` | Upload a document (PDF, DOCX, TXT); ingestion runs in background |
| `GET`    | `/api/documents?session_id={id}` | List documents in a session                                      |
| `DELETE` | `/api/documents/{document_id}`   | Delete a document and its chunks                                 |

**Example — upload document:**

```bash
curl -X POST "http://localhost:8000/api/documents?session_id=<SESSION_ID>" \
  -F "file=@contract.pdf"
```

```json
{
  "id": "a1b2c3d4-...",
  "session_id": "3fa85f64-...",
  "original_filename": "contract.pdf",
  "file_type": "pdf",
  "status": "uploaded",
  "page_count": null,
  "uploaded_at": "2026-09-24T01:05:00Z"
}
```

---

### Chat

| Method   | Endpoint      | Description                                    |
| -------- | ------------- | ---------------------------------------------- |
| `POST` | `/api/chat` | Send a message; returns an**SSE stream** |

**Example — send a message:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>", "message": "What are the termination clauses?"}'
```

**SSE event stream format:**

```
event: stage
data: {"stage": "Understand", "status": "running"}

event: stage
data: {"stage": "Plan", "status": "done", "summary": "Routing: document"}

0:"The contract contains three termination clauses..."

event: citations
data: [{"source_type": "document", "document_filename": "contract.pdf", "page_number": 4, ...}]

event: done
data: {"routing_mode": "document"}
```

---

### Health

| Method  | Endpoint    | Description                 |
| ------- | ----------- | --------------------------- |
| `GET` | `/health` | Returns`{"status": "ok"}` |

---

## Environment Variables

Create `backend/.env` by copying `backend/.env.example`:

```bash
cp backend/.env.example backend/.env
```

| Variable                | Description                                       | Required | Example                                                |
| ----------------------- | ------------------------------------------------- | -------- | ------------------------------------------------------ |
| `DATABASE_URL`        | Async PostgreSQL connection string (pooled)       | ✅       | `postgresql+asyncpg://user:pass@host/db?ssl=require` |
| `DATABASE_URL_DIRECT` | Direct (non-pooled) connection — used by Alembic | ✅       | Same format, no pooler port                            |
| `LLM_PROVIDER`        | LLM provider — currently`groq`                 | ✅       | `groq`                                               |
| `GROQ_API_KEY`        | Your Groq API key                                 | ✅       | `gsk_...`                                            |
| `GROQ_MODEL`          | Groq model identifier                             | ✅       | `openai/gpt-oss-120b`                                |
| `EMBEDDING_PROVIDER`  | `fastembed` (local, free) or `voyage`         | ✅       | `fastembed`                                          |
| `TAVILY_API_KEY`      | Tavily API key for web search                     | ✅       | `tvly-...`                                           |
| `FRONTEND_ORIGIN`     | Allowed CORS origin                               | ✅       | `http://localhost:5173`                              |

> **Tip:** `fastembed` runs entirely locally using ONNX models — no API key or internet connection required for embeddings.
# judiciary-ai
