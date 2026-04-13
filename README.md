# Linkedin-Assistant
# Prospera — AI-Powered Outreach Intelligence

> **Find anyone. Reach everyone.**  
> A multi-agent AI pipeline that automates B2B lead generation from search to personalized message — end to end.


## What is Prospera?

Cold outreach is broken. Most people spend hours manually searching LinkedIn, guessing who to contact, and writing generic messages that get ignored.

Prospera fixes this with a **6-agent AI pipeline**:

1. You type one line — *"ML internships Kolkata remote"*
2. It finds the right companies
3. Finds the right people at those companies
4. Enriches every profile with hooks and context
5. Scores leads by **your** priorities
6. Writes personalized outreach for each contact

No templates. No guesswork. No manual research.

---

## Pipeline Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│  Agent 1 — Company Discovery    │  Finds actively hiring companies
│  Serper + LLM extraction        │  ranked by fit score
└─────────────────┬───────────────┘
                  │ companies[]
                  ▼
┌─────────────────────────────────┐
│  Agent 2 — People Finder        │  Discovers founders, CTOs,
│  Serper + LLM extraction        │  hiring managers at each company
└─────────────────┬───────────────┘
                  │ discovered_people[]
                  ▼
┌─────────────────────────────────┐
│  Agent 3 — Enrichment           │  Deepens every profile with
│  Serper + Apollo + LLM          │  hooks, emails, company intel
└─────────────────┬───────────────┘
                  │ enriched_people[]
                  ▼
┌─────────────────────────────────┐
│  Agent 4 — Scoring              │  Interviews user about priorities
│  Human-in-the-loop + LLM        │  then scores leads by custom weights
└─────────────────┬───────────────┘
                  │ scored_leads[]
                  ▼
┌─────────────────────────────────┐
│  Agent 5 — Targeting            │  Filters, deduplicates, verifies
│  Abstract API + LLM             │  emails, assigns HIGH/MEDIUM/LOW
└─────────────────┬───────────────┘
                  │ target_list[]
                  ▼
┌─────────────────────────────────┐
│  Agent 6 — Message Generator    │  Writes LinkedIn request, DM,
│  LLM + quality scorer           │  cold email and follow-up per contact
└─────────────────────────────────┘
```

All 6 agents share a **single unified state** that flows through the entire pipeline. Each agent reads what it needs and writes its output back — no data loss between steps.

---

## Features

- 🏢 **Smart Company Discovery** — Finds companies actively hiring for your role, ranked by fit score
- 👤 **Decision Maker Finder** — Identifies founders, CTOs and hiring managers via web intelligence
- ✨ **Deep Enrichment** — Gathers recent posts, hooks, email patterns, funding stage, tech stack
- 📊 **Priority Interview** — AI asks you domain-specific questions, builds a custom scoring config
- 🎯 **Intelligent Targeting** — Filters students/duplicates, keeps top 4 per company, verifies emails
- ✉️ **Personalized Outreach** — Every message references a specific hook — not a template
- 🔄 **Auto Quality Check** — Scores messages on personalization, clarity, CTA, spam risk — rewrites if needed
- 📅 **7-Day Campaign Plan** — Tells you exactly who to contact on which day
- 🌙 **Beautiful UI** — Space/moon themed React frontend with live WebSocket progress
- ⚡ **Real-time Updates** — Watch each agent run live with animated progress steps

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | Mistral AI (mistral-large-latest) |
| Web Search | Serper API |
| Company Enrichment | Apollo.io (free org endpoint) |
| Email Verification | Abstract API |
| Backend | FastAPI + WebSocket |
| Frontend | React 18 + Tailwind CSS |
| State Management | TypedDict unified state |

---

## Project Structure

```
Prospera/
├── Agents/
│   ├── agent_1/          # Company Discovery
│   │   ├── nodes.py      # domain_input, search_context, company_extraction
│   │   └── graph.py
│   ├── agent_2/          # People Finder
│   │   ├── nodes_2.py    # decide_targets, search_people, extract_people
│   │   └── graph_2.py
│   ├── agent_3/          # Enrichment
│   │   ├── node_3.py     # clean_profiles, enrich_people, enrich_companies, email_guess
│   │   └── graph_3.py
│   ├── agent_4/          # Scoring
│   │   ├── node_4.py     # generate_questions, build_scoring_config, scoring
│   │   └── graph_4.py
│   ├── agent_5/          # Targeting
│   │   ├── node_5.py     # filter_targets, email_verify, shortlist, build_dashboard
│   │   └── graph_5.py
│   └── agent_6/          # Message Generator
│       ├── node_6.py     # build_sender_bio, generate_messages, quality_score, campaign_planner
│       └── graph_6.py
│
├── backend/
│   ├── main.py           # FastAPI app + WebSocket
│   ├── connections.py    # Shared WebSocket store
│   ├── schemas.py        # Pydantic models
│   ├── routes/
│   │   └── pipeline.py   # All API endpoints
│   └── services/
│       └── session.py    # In-memory session management
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api/client.js
│       ├── components/
│       │   ├── SpaceBackground.jsx  # Moon + stars canvas animation
│       │   ├── SearchStep.jsx       # Search + live WebSocket progress
│       │   ├── ResultsStep.jsx      # Company + people results
│       │   ├── InterviewStep.jsx    # Priority questions UI
│       │   ├── ScoredLeads.jsx      # Ranked leads
│       │   ├── Dashboard.jsx        # Pipeline stats + CTA
│       │   ├── SenderProfile.jsx    # User profile form
│       │   └── Messages.jsx         # Generated outreach + campaign plan
│       └── index.css
│
├── core/
│   ├── state.py          # Unified AgentState TypedDict
│   ├── llm.py            # LLM initialization
│   └── config.py         # API keys
│
└── main.py               # Terminal runner (for testing without UI)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for: Mistral AI, Serper, Apollo.io (optional), Abstract API (optional)

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/prospera.git
cd prospera
```

### 2. Set up Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install langgraph langchain-mistralai fastapi uvicorn python-multipart requests
```

### 3. Configure API keys

Create `core/config.py`:

```python
SERPER_API_KEY   = "your_serper_api_key"       # serper.dev — 2500 free searches
MISTRAL_API_KEY  = "your_mistral_api_key"       # console.mistral.ai — free tier
APPOLO_API_KEY   = "your_apollo_api_key"        # apollo.io — free org enrichment
ABSTRACT_API_KEY = "your_abstract_api_key"      # abstractapi.com — 100 free verifications
```

### 4. Set up frontend

```bash
cd frontend
npm install
```

### 5. Run the backend

```bash
# From project root
cd ..
uvicorn backend.main:app --reload --port 8000
```

### 6. Run the frontend

```bash
# In a new terminal
cd frontend
npm run dev
```

Open **http://localhost:5173**

---

## How It Works

### The Search → Extract Pattern

Every agent follows the same principle:

```
Serper API  →  Raw web data  →  LLM extraction  →  Structured output
```

The LLM **never invents** companies or people. It reads real search results and extracts structured information. This is what makes outputs trustworthy and grounded.

### Unified State

```python
class AgentState(TypedDict):
    # Agent 1
    domain: str
    intent: dict
    companies: list

    # Agent 2
    discovered_people: list

    # Agent 3
    enriched_people: list
    enriched_companies: list

    # Agent 4
    interview_questions: list
    human_answers: dict
    scoring_config: dict
    scored_leads: list

    # Agent 5
    target_list: list
    dashboard_stats: dict

    # Agent 6
    sender_profile: dict
    generated_messages: list
    campaign_plan: dict

    # Control
    logs: list
    error: Optional[str]
    step: str
```

One state object flows through all 6 agents. No data loss. No complex handoffs.

### Fault Tolerance

Every node has conditional edges:

```python
builder.add_conditional_edges(
    "search_context",
    lambda s: s.get("step"),
    {
        "context_fetched": "company_extraction",
        "context_failed":  END   # ← stop cleanly, don't crash
    }
)
```

If any step fails, the pipeline stops gracefully with a clear error message.

### Human-in-the-Loop

Agent 4 doesn't use hardcoded scoring weights. It interviews the user first:

```
AI generates context-aware questions based on the search domain
User answers via UI (multi-select options)
LLM converts answers into a custom scoring weight config
Scoring engine uses those weights to rank all leads
```

This means someone searching "DevOps jobs" gets questions about cloud providers and CI/CD stacks — not generic B2B questions.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/session/new` | Create new session |
| POST | `/api/search` | Run agents 1+2+3, returns companies + people |
| POST | `/api/interview/questions` | Generate priority questions |
| POST | `/api/interview/submit` | Submit answers, score leads |
| POST | `/api/target` | Filter + shortlist + dashboard |
| POST | `/api/messages/generate` | Generate personalized outreach |
| GET  | `/api/session/{id}` | Get session state |
| WS   | `/ws/{session_id}` | Live progress updates |

Full API docs available at **http://localhost:8000/docs** when running.

---

## Key Design Decisions

**Why LangGraph?**
LangGraph provides proper graph-based agent orchestration with conditional edges, state management and fault tolerance. It's more suitable for complex multi-step pipelines than simple LLM chains.

**Why not use Apollo/Hunter for people search?**
Their free tiers are too limited for real use. Serper + LLM extraction gives comparable results at scale without API paywalls. Apollo is used only for company enrichment where its free `organization/enrich` endpoint works well.

**Why split Agent 4 into two graphs?**
The interview requires a human pause between question generation and answer submission. Splitting into `build_questions_graph` and `build_scoring_graph` keeps the LangGraph execution clean without needing LangGraph's interrupt mechanism.

**Why run agents in thread pools?**
LangGraph `.invoke()` is synchronous but FastAPI is async. Using `run_in_executor` keeps the event loop free so WebSocket progress updates fire between agents instead of blocking.

---

## Roadmap

- [ ] SQLite memory layer — skip already-contacted leads
- [ ] Supabase integration for persistent storage
- [ ] Export to CSV / Notion / HubSpot
- [ ] LinkedIn OAuth for direct message sending
- [ ] Multi-user support
- [ ] Docker deployment
- [ ] Supabase + Vercel production deploy

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## License

MIT — use it, build on it, make it better.

---

## Author

Built by **Tredip Debnath**

If this saved you hours of manual LinkedIn research, consider giving it a ⭐

---

*Prospera — because outreach should be intelligent, not exhausting.*
