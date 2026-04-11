from fastapi import APIRouter , HTTPException
from backend.schemas import SearchRequest , AnswersRequest, SenderProfileRequest, SessionResponse
from backend.services.session import*
from Agents.agent_1.graph import build_graph
from Agents.agent_2.graph_2 import build_people_finder_graph
from Agents.agent_3.graph_3 import build_enrichment_graph
from Agents.agent_4.graph_4 import build_scoring_graph,build_questions_graph
from Agents.agent_5.graph_5 import build_targeting_graph
from Agents.agent_6.graph_6 import build_message_generator_graph


agent1 = build_graph()
agent2 = build_people_finder_graph()
agent3 = build_enrichment_graph()
agent4_questions = build_questions_graph() 
agent4_scoring   = build_scoring_graph() 
agent5 = build_targeting_graph() 
agent6 = build_message_generator_graph()

router = APIRouter() 

def _response(session_id: str , state:dict , data: dict) -> dict:
    return{
        "session_id": session_id,
        "step":       state.get("step", ""),
        "data":       data,
        "logs":       state.get("logs", []),
        "error":      state.get("error")
    }

@router.post("/search")
async def search(req: SearchRequest):
    session_id = req.session_id or create_session()
    state = get_session(session_id)

    if not req.domain.strip():
        raise HTTPException(status_code=400, detail="Search query is required")
    
    state["domain"] = req.domain.strip()
    state["logs"]   = []

    try :
        
        # Agent 1
        state = agent1.invoke(state)
        if state.get("error"):
            update_session(session_id, state)
            return _response(session_id, state,{})
        
        # Agent 2 
        state = agent2.invoke(state)
        if state.get("error"):
            update_session(session_id, state)
            return _response(session_id,state,{})
        
        # Agent 3 
        state = agent3.invoke(state)
        
        update_session(session_id, state)

        return _response(session_id, state, {
            "companies":          state.get("companies", []),
            "enriched_people":    state.get("enriched_people", []),
            "enriched_companies": state.get("enriched_companies", []),
            "intent":             state.get("intent", {}),
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ── POST /api/interview/questions ─────────────────────────────
# Runs Agent 4 question generation only
# Returns: interview_questions

@router.post("/interview/questions")
async def get_questions(req: dict):
    session_id  = req.get("session_id")
    state       = get_session(session_id)
    state["logs"] = []

    try:
        state = agent4_questions.invoke(state)   # ← use questions graph
        update_session(session_id, state)
        return _response(session_id, state, {
            "questions": state.get("interview_questions", [])
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── POST /api/interview/submit ────────────────────────────────
# Submits answers + runs scoring (Agent 4 scoring node)
# Returns: scored_leads, scoring_config
@router.post("/interview/submit")
async def submit_answers(req: AnswersRequest):
    session_id = req.session_id
    state      = get_session(session_id)
    state["human_answers"] = req.answers
    state["logs"]          = []

    try:
        state = agent4_scoring.invoke(state)     # ← use scoring graph
        update_session(session_id, state)
        return _response(session_id, state, {
            "scored_leads":   state.get("scored_leads", []),
            "scoring_config": state.get("scoring_config", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
# ── POST /api/target ──────────────────────────────────────────
# Runs Agent 5 — filtering, email verify, shortlist, dashboard
# Returns: target_list, dashboard_stats
@router.post("/target")
async def target(req: dict):
    session_id = req.get("session")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    state = get_session(session_id)
    state["logs"] = []

    try:
        state = agent5.invoke(state)
        update_session(session_id, state)

        return _response(session_id, state, {
            "target_list":    state.get("target_list", []),
            "dashboard_stats": state.get("dashboard_stats", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Runs Agent 6
# Returns: generated_messages, campaign_plan
@router.post("/message/generate")
async def generate_messages(req: SenderProfileRequest) :
    session_id = req.session_id
    state = get_session(session_id)

    if not session_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state["sender_profile"] = {
        "name":    req.name    or "Candidate",
        "college": req.college or "",
        "degree":  req.degree  or "",
        "year":    req.year    or "",
        "skills":  req.skills  or [],
        "project": req.project or "",
        "achieve": req.achieve or "",
        "linkedin": req.linkedin or "",
        "goal":    req.goal    or "opportunities",
        "bio":     ""
    }

    state["logs"] =[]

    try:
        state = agent6.invoke(state)
        update_session(session_id, state)

        return _response(session_id, state, {
            "generated_messages": state.get("generated_messages", []),
            "campaign_plan":      state.get("campaign_plan", {}),
            "sender_profile":     state.get("sender_profile", {}),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/session/{session_id} ─────────────────────────────
# Get current session state
@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "step": state.get("step"), "state": state}


# ── DELETE /api/session/{session_id} ─────────────────────────
@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    from backend.services.session import delete_session
    delete_session(session_id)
    return {"message": "Session cleared"}
