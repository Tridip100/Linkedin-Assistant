import asyncio
from functools import partial
from fastapi import APIRouter, HTTPException
from backend.schemas import SearchRequest, AnswersRequest, SenderProfileRequest
from backend.services.session import create_session, get_session, update_session, delete_session

from Agents.agent_1.graph import build_graph
from Agents.agent_2.graph_2 import build_people_finder_graph
from Agents.agent_3.graph_3 import build_enrichment_graph
from Agents.agent_4.graph_4 import build_questions_graph, build_scoring_graph
from Agents.agent_5.graph_5 import build_targeting_graph
from Agents.agent_6.graph_6 import build_message_generator_graph

# ── Build all graphs once at startup ─────────────────────────
agent1           = build_graph()
agent2           = build_people_finder_graph()
agent3           = build_enrichment_graph()
agent4_questions = build_questions_graph()
agent4_scoring   = build_scoring_graph()
agent5           = build_targeting_graph()
agent6           = build_message_generator_graph()

router = APIRouter()


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

async def run_agent(agent, state: dict) -> dict:
    """
    Run a synchronous LangGraph agent in a thread pool
    so it doesn't block the FastAPI event loop.
    This allows WebSocket pushes to fire between agents.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(agent.invoke, state))
    return result


async def push(session_id: str, event: dict):
    """Push a progress event to the frontend via WebSocket."""
    try:
        from backend.connections import connections
        ws = connections.get(session_id)
        if ws:
            await ws.send_json(event)
            print(f"  [WS] → {session_id[:8]}... agent:{event.get('agent')} status:{event.get('status')}")
        else:
            print(f"  [WS] No connection for session: {session_id[:8]}...")
    except Exception as e:
        print(f"  [WS] Push failed: {e}")


def _response(session_id: str, state: dict, data: dict) -> dict:
    return {
        "session_id": session_id,
        "step":       state.get("step", ""),
        "data":       data,
        "logs":       state.get("logs", []),
        "error":      state.get("error")
    }


# ──────────────────────────────────────────────────────────────
# SESSION
# ──────────────────────────────────────────────────────────────

@router.post("/session/new")
async def new_session():
    session_id = create_session()
    print(f"  [Session] Created: {session_id}")
    return {"session_id": session_id}


# ──────────────────────────────────────────────────────────────
# SEARCH — Agent 1 + 2 + 3
# ──────────────────────────────────────────────────────────────

@router.post("/search")
async def search(req: SearchRequest):
    session_id = req.session_id or create_session()
    state      = get_session(session_id)

    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="Search query is required")

    state["domain"] = req.domain.strip()
    state["logs"]   = []

    try:
        # ── Agent 1 — Company Discovery ──────────────────────
        await push(session_id, {
            "agent": 1, "status": "running",
            "msg": "Searching for matching companies..."
        })

        state = await run_agent(agent1, state)

        if state.get("error"):
            await push(session_id, {
                "agent": 1, "status": "error",
                "msg": state["error"]
            })
            update_session(session_id, state)
            return _response(session_id, state, {})

        await push(session_id, {
            "agent": 1, "status": "done",
            "msg": f"Found {len(state.get('companies', []))} companies"
        })

        # ── Agent 2 — People Finder ───────────────────────────
        await push(session_id, {
            "agent": 2, "status": "running",
            "msg": "Finding founders and decision makers..."
        })

        state = await run_agent(agent2, state)

        if state.get("error"):
            await push(session_id, {
                "agent": 2, "status": "error",
                "msg": state["error"]
            })
            update_session(session_id, state)
            return _response(session_id, state, {})

        await push(session_id, {
            "agent": 2, "status": "done",
            "msg": f"Discovered {len(state.get('discovered_people', []))} contacts"
        })

        # ── Agent 3 — Enrichment ──────────────────────────────
        await push(session_id, {
            "agent": 3, "status": "running",
            "msg": "Enriching profiles with web intelligence..."
        })

        state = await run_agent(agent3, state)

        await push(session_id, {
            "agent": 3, "status": "done",
            "msg": f"Enriched {len(state.get('enriched_people', []))} profiles"
        })

        # ── All done ──────────────────────────────────────────
        await push(session_id, {
            "agent": "all", "status": "complete",
            "msg": "Ready!"
        })

        update_session(session_id, state)

        return _response(session_id, state, {
            "companies":          state.get("companies", []),
            "enriched_people":    state.get("enriched_people", []),
            "enriched_companies": state.get("enriched_companies", []),
            "intent":             state.get("intent", {}),
        })

    except Exception as e:
        await push(session_id, {
            "agent": "all", "status": "error",
            "msg": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# INTERVIEW — Agent 4 (questions)
# ──────────────────────────────────────────────────────────────

@router.post("/interview/questions")
async def get_questions(req: dict):
    session_id = req.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    state         = get_session(session_id)
    state["logs"] = []

    try:
        state = await run_agent(agent4_questions, state)
        update_session(session_id, state)
        return _response(session_id, state, {
            "questions": state.get("interview_questions", [])
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# INTERVIEW — Agent 4 (scoring)
# ──────────────────────────────────────────────────────────────

@router.post("/interview/submit")
async def submit_answers(req: AnswersRequest):
    session_id = req.session_id
    state      = get_session(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    state["human_answers"] = req.answers
    state["logs"]          = []

    try:
        state = await run_agent(agent4_scoring, state)
        update_session(session_id, state)
        return _response(session_id, state, {
            "scored_leads":   state.get("scored_leads", []),
            "scoring_config": state.get("scoring_config", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# TARGET — Agent 5
# ──────────────────────────────────────────────────────────────

@router.post("/target")
async def target(req: dict):
    session_id = req.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    state         = get_session(session_id)
    state["logs"] = []

    try:
        state = await run_agent(agent5, state)
        update_session(session_id, state)
        return _response(session_id, state, {
            "target_list":     state.get("target_list", []),
            "dashboard_stats": state.get("dashboard_stats", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# MESSAGES — Agent 6
# ──────────────────────────────────────────────────────────────

@router.post("/messages/generate")
async def generate_messages(req: SenderProfileRequest):
    session_id = req.session_id
    state      = get_session(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    state["sender_profile"] = {
        "name":     req.name     or "Candidate",
        "college":  req.college  or "",
        "degree":   req.degree   or "",
        "year":     req.year     or "",
        "skills":   req.skills   or [],
        "project":  req.project  or "",
        "achieve":  req.achieve  or "",
        "linkedin": req.linkedin or "",
        "goal":     req.goal     or "opportunities",
        "bio":      ""
    }
    state["logs"] = []

    try:
        state = await run_agent(agent6, state)
        update_session(session_id, state)
        return _response(session_id, state, {
            "generated_messages": state.get("generated_messages", []),
            "campaign_plan":      state.get("campaign_plan", {}),
            "sender_profile":     state.get("sender_profile", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────
# SESSION UTILS
# ──────────────────────────────────────────────────────────────

@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "step":       state.get("step"),
        "state":      state
    }


@router.delete("/session/{session_id}")
async def clear_session_route(session_id: str):
    delete_session(session_id)
    return {"message": "Session cleared"}