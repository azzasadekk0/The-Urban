# The Urban — Egyptian Building Code AI Expert System

<p align="center">
  <b>An AI-powered legal consultation system for Egyptian urban planning and building regulations.</b><br/>
  Powered by a multi-agent RAG pipeline with strict legal hierarchy enforcement.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi"/>
  <img src="https://img.shields.io/badge/Next.js-15-black?style=flat-square&logo=next.js"/>
  <img src="https://img.shields.io/badge/LangGraph-Agentic-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/ChromaDB-Vector_Store-purple?style=flat-square"/>
  <img src="https://img.shields.io/badge/GPT--4o-LLM-teal?style=flat-square&logo=openai"/>
</p>

---

## Features

-  **Agentic RAG Pipeline** — Multi-node LangGraph agent: Analyze → Retrieve → Calculate → Finalize
- **Strict Legal Hierarchy** — 6-tier priority system enforcing Egyptian law precedence (Decree 943/2024 overrides all)
- *Conflict Arbitration** — Automatically detects and resolves conflicts between laws; sends `⚠️ CONFLICT NOTICE` to LLM for context-aware resolution
- **8 Legal Documents** — Covers building codes, fire codes, parking regulations, reconciliation law, and urban planning conditions
- **Bilingual Support** — Fully responds in Arabic or English based on the user's question language (auto-detected)
- **Session History** — Each conversation is persisted per-session in SQLite; browseable from the History tab
-  **Live Public URL** — Integrated ngrok tunnel auto-publishes the app at a public HTTPS URL on every startup
-  **Session Isolation** — No cross-session context leakage; new conversations always start fresh
- **Calculation Support** — Built-in building area and setback calculation node with disclaimer output
- **Source Citations** — Every answer cites the exact law(s) used, with priority tags

---

## How It Works

```
User Question
     │
     ▼
┌─────────────────────┐
│   ANALYZE NODE      │  → Detects language, topics (parking, fire, reconciliation…)
│                     │    Flags if calculation is needed
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   RETRIEVE NODE     │  → Priority-weighted vector search across 8 ChromaDB collections
│                     │    Score formula: raw_score - (priority × 0.02)
│                     │    Conflict detection → CONFLICT NOTICE injected into context
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CALCULATE NODE     │  → (Optional) Computes floor area, setbacks, parking ratios
│                     │    Only runs if requires_calculation = True
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   FINALIZE NODE     │  → GPT-4o generates the legal answer
│                     │    Enforces law priority (P1–P6), adds disclaimers,
│                     │    responds in the same language as the question
└──────────┬──────────┘
           │
           ▼
  Structured Legal Response
  (Answer + Sources + Active Laws)
```


---

## Project Structure

```
The Urban/
├── backend/                        # FastAPI + LangGraph backend
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Settings, document registry, law priorities
│   ├── session_manager.py          # SQLite-backed session & history manager
│   ├── agents/
│   │   ├── graph.py                # LangGraph pipeline definition
│   │   ├── state.py                # Shared agent state schema
│   │   └── nodes/
│   │       ├── analyze.py          # Query analysis node
│   │       ├── retrieve.py         # Priority-weighted RAG retrieval node
│   │       ├── calculate.py        # Building calculation node
│   │       └── finalize.py         # LLM answer generation + legal formatting
│   ├── rag/
│   │   ├── ingestor.py             # PDF chunking + ChromaDB ingestion
│   │   ├── retriever.py            # Semantic search + conflict detection
│   │   └── vector_store.py         # ChromaDB client wrapper
│   └── api/routes/
│       ├── chat.py                 # Chat, session, history endpoints
│       └── health.py               # Health, status, ingest endpoints
│
├── Frontend/                       # Next.js 15 + TypeScript UI
│   ├── app/
│   │   ├── page.tsx                # Main dashboard (routing between views)
│   │   ├── layout.tsx              # Root layout + fonts
│   │   └── globals.css             # Global styles
│   ├── components/urban/
│   │   ├── chat-content.tsx        # Chat view with real-time RAG responses
│   │   ├── sidebar-nav.tsx         # Collapsible sidebar navigation
│   │   ├── history-content.tsx     # Session history browser
│   │   └── knowledge-index.tsx     # Legal document index viewer
│   └── next.config.mjs             # API proxy to backend (port 8001)
│
├── data/pdfs/                      
├── vector_db/                      # ChromaDB persistent storage (auto-generated)
├── sessions.db                     # SQLite session history (auto-generated)
├── fast_ingest.py                  # Standalone script to ingest PDFs into vector DB
├── ngrok_tunnel.py                 # ngrok tunnel launcher (public URL)
├── start.ps1                       # One-command startup script (Windows)
├── requirements.txt                # Python dependencies
└── .env.example                    # Environment variables template
```

---

## Setup

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12+ |
| Node.js | 18+ |
| pnpm | 9+ |
| OpenAI API Key | Required |
| ngrok Auth Token | Optional (for public URL) |

### 1. Clone the Repository

```bash
git clone https://github.com/azzasadekk0/the-urban.git
cd the-urban
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
BACKEND_URL=http://localhost:8001
NGROK_AUTH_TOKEN=your_ngrok_token_here   # Optional
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd Frontend
pnpm install
cd ..
```

---

## Usage

### Start Everything (Recommended)

```powershell
.\start.ps1
```

This single command will:
1. Kill any stale processes on ports 8001 and 3000
2. Start the FastAPI backend at `http://localhost:8001`
3. Start the Next.js frontend at `http://localhost:3000`
4. Launch an ngrok tunnel and print the live public URL

### Manual Start (Development)

**Backend:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend:**
```bash
cd Frontend
pnpm run dev
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message (creates session if none provided) |
| `GET` | `/api/chat/sessions` | List all past sessions |
| `GET` | `/api/chat/history/{session_id}` | Get full history of a session |
| `DELETE` | `/api/chat/{session_id}` | Delete a session |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/status` | Document ingestion status |
| `POST` | `/api/ingest` | Trigger re-ingestion of documents |


---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | GPT-4o (OpenAI) |
| **Embeddings** | `text-embedding-3-large` (OpenAI) |
| **Agent Framework** | LangGraph |
| **Vector Database** | ChromaDB |
| **Backend** | FastAPI + Uvicorn |
| **Session Storage** | SQLite (via aiosqlite) |
| **Frontend** | Next.js 15 + TypeScript + Tailwind |
| **UI Components** | shadcn/ui |
| **Public Tunnel** | ngrok (pyngrok) |
| **Startup Script** | PowerShell (.ps1) |

---
