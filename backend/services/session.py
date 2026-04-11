import uuid
from typing import Dict , Any

_session: Dict[str, Dict[str,Any]] ={}

def create_session()-> str:
    session_id = str(uuid.uuid4())
    _session[session_id] = _get_initial_state()
    return session_id

def get_session(session_id:str) -> Dict[str,Any] :
    return _session.get(session_id, {})

def update_session(session_id: str , state:Dict[str,Any]):
    _session[session_id] = state

def delete_session(session_id: str):
    _session.pop(session_id, None)

def _get_initial_state() -> Dict[str, Any]:
    return {
        "domain": "", "raw_text": "", "companies": [],
        "selected_company": None, "company_insights": None,
        "intent": {},
        "target_personas": {}, "raw_people_results": [],
        "discovered_people": [],
        "enriched_people": [], "enriched_companies": [],
        "interview_questions": [], "human_answers": {},
        "scoring_config": {}, "scored_leads": [],
        "target_list": [], "dashboard_stats": {},
        "sender_profile": {}, "generated_messages": [],
        "campaign_plan": {},
        "logs": [], "messages": [], "error": None, "step": "start"
    }

session_store = {
    "create" : create_session,
    "get" : get_session,
    "update" : update_session,
    "delete" : delete_session
}