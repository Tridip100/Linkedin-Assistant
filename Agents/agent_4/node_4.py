import re
import json
from core.state import AgentState
from core.llm import llm


def _parse_llm_json(raw: str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)

def _log(logs: list, level: str, msg: str):
    logs.append({"level": level, "msg": msg})


def generate_questions_node(state: AgentState) -> AgentState:
    enriched_people = state.get("enriched_people", [])
    intent          = state.get("intent", {})
    companies       = state.get("enriched_companies", [])
    logs            = []

    if not enriched_people:
        return {**state, "error": "No enriched people to score.", "step": "interview_failed", "logs": logs}

    prompt = f"""
You are a B2B lead scoring assistant.
User searched: Role:{intent.get('role')}, Type:{intent.get('opportunity_type')},
Location:{intent.get('location')}, Mode:{intent.get('work_mode')}, Level:{intent.get('experience_level')}
Companies: {[c.get('name') for c in companies[:5]]}
People: {len(enriched_people)} contacts

Generate 5-6 smart relevant questions with 3-4 options each.
Return ONLY raw JSON. Start with [ end with ].
[
  {{
    "id": "q1",
    "question": "Question text",
    "options": ["Option 1", "Option 2", "Option 3"],
    "multi_select": true,
    "weight_key": "seniority"
  }}
]
Rules: multi_select true for all, weight_key one of: seniority|company_stage|location_match|has_email|has_linkedin|has_hook|tech_stack|confidence, specific to their domain.
"""
    try:
        raw       = llm.invoke(prompt).content.strip()
        questions = _parse_llm_json(raw)
        _log(logs, "success", f"Generated {len(questions)} questions")
        return {**state, "interview_questions": questions, "step": "questions_generated", "logs": logs}
    except Exception as e:
        _log(logs, "warning", f"Using fallback questions: {e}")
        questions = [
            {"id": "q1", "question": "What seniority level to prioritize?", "options": ["Founders/C-suite only", "VP/Director level", "Managers fine", "Anyone works"], "multi_select": True, "weight_key": "seniority"},
            {"id": "q2", "question": "How important is location?", "options": ["Must be target city", "Same country preferred", "Doesn't matter"], "multi_select": True, "weight_key": "location_match"},
            {"id": "q3", "question": "How do you plan to reach out?", "options": ["Email only", "LinkedIn DM", "Both preferred", "Either works"], "multi_select": True, "weight_key": "has_linkedin"},
            {"id": "q4", "question": "Does tech stack matter?", "options": ["Must match domain", "Modern stack preferred", "Doesn't matter"], "multi_select": True, "weight_key": "tech_stack"},
            {"id": "q5", "question": "How important is a personal talking point?", "options": ["Very — only with hook", "Preferred not required", "Doesn't matter"], "multi_select": True, "weight_key": "has_hook"},
        ]
        return {**state, "interview_questions": questions, "step": "questions_generated", "logs": logs}


def build_scoring_config_node(state: AgentState) -> AgentState:
    answers  = state.get("human_answers", {})
    intent   = state.get("intent", {})
    location = intent.get("location", "any")
    logs     = []

    if not answers:
        return {**state, "error": "No answers provided.", "step": "config_failed", "logs": logs}

    answers_text = "\n".join(f"  {v['question']} → {v['answer']}" for v in answers.values())

    prompt = f"""
You are a B2B lead scoring strategist.
User location: {location}, Role: {intent.get('role')}

Answers:
{answers_text}

Return ONLY raw JSON. Start with {{ end with }}.
{{
  "weights": {{
    "seniority": 0.0, "company_stage": 0.0, "location_match": 0.0,
    "has_email": 0.0, "has_linkedin": 0.0, "has_hook": 0.0,
    "tech_stack": 0.0, "confidence": 0.0
  }},
  "filters": {{
    "min_seniority": [],
    "preferred_stages": [],
    "require_email": false,
    "require_linkedin": true,
    "require_hook": false,
    "preferred_location": "{location}"
  }},
  "goal": "one sentence outreach goal"
}}
CRITICAL: weights sum to 1.0. min_seniority values: c_suite|vp|director|manager|individual_contributor.
min_seniority = MINIMUM and above: managers→["c_suite","vp","director","manager"].
NEVER just ["manager"]. require_hook=true ONLY if explicitly very important. Unimportant→0.05.
"""
    try:
        raw    = llm.invoke(prompt).content.strip()
        config = _parse_llm_json(raw)
        _log(logs, "success", f"Config: {config.get('goal')}")
        return {**state, "scoring_config": config, "step": "config_built", "logs": logs}
    except Exception as e:
        _log(logs, "warning", f"Using default config: {e}")
        default = {
            "weights": {"seniority": 0.25, "company_stage": 0.15, "location_match": 0.15,
                        "has_email": 0.10, "has_linkedin": 0.10, "has_hook": 0.15,
                        "tech_stack": 0.05, "confidence": 0.05},
            "filters": {"min_seniority": ["c_suite", "vp"], "preferred_stages": [],
                        "require_email": False, "require_linkedin": True,
                        "require_hook": False, "preferred_location": location},
            "goal": "General B2B outreach"
        }
        return {**state, "scoring_config": default, "step": "config_built", "logs": logs}


def scoring_node(state: AgentState) -> AgentState:
    people    = state.get("enriched_people", [])
    companies = state.get("enriched_companies", [])
    config    = state.get("scoring_config", {})
    intent    = state.get("intent", {})
    logs      = []

    weights = config.get("weights", {})
    filters = config.get("filters", {})
    company_map = {c.get("name", ""): c for c in companies}

    seniority_rank = {"c_suite": 100, "vp": 85, "director": 70, "manager": 50, "individual_contributor": 30}
    funding_rank   = {"Series C": 100, "Series B": 90, "Series A": 80, "Seed": 70, "Pre-seed": 60, "Bootstrapped": 40, "Public": 50, "Unknown": 20}

    preferred_stages   = filters.get("preferred_stages", [])
    preferred_location = filters.get("preferred_location", "any").lower()
    min_seniority      = filters.get("min_seniority", [])
    require_email      = filters.get("require_email", False)
    require_linkedin   = filters.get("require_linkedin", False)
    require_hook       = filters.get("require_hook", False)
    intent_location    = intent.get("location", "any").lower()

    if min_seniority and "manager" in min_seniority and "c_suite" not in min_seniority:
        min_seniority = ["c_suite", "vp", "director", "manager"]
        _log(logs, "info", "Auto-fixed min_seniority")

    scored = []

    for p in people:
        name       = p.get("name", "")
        seniority  = p.get("seniority", "individual_contributor")
        company    = p.get("company", "")
        linkedin   = p.get("linkedin_url", "")
        email      = p.get("email_hint", "")
        hook       = p.get("best_hook", "")
        location   = p.get("location", "").lower()
        confidence = p.get("confidence", 0)

        co_data       = company_map.get(company, {})
        funding_stage = co_data.get("funding_stage", "Unknown")
        tech_stack    = [t.lower() for t in co_data.get("tech_stack", [])]
        pain_points   = co_data.get("pain_points", [])

        if require_email    and not email:    continue
        if require_linkedin and not linkedin: continue
        if require_hook     and not hook:     continue
        if min_seniority and len(min_seniority) > 0 and seniority not in min_seniority:
            continue

        seniority_score = seniority_rank.get(seniority, 30)
        stage_score     = funding_rank.get(funding_stage, 20)
        if preferred_stages and funding_stage in preferred_stages:
            stage_score = min(stage_score + 20, 100)

        if preferred_location == "any" or intent_location == "any":
            location_score = 70
        elif preferred_location in location or intent_location in location:
            location_score = 100
        elif "india" in location:
            location_score = 60
        else:
            location_score = 30

        email_score    = 100 if email    else 0
        linkedin_score = 100 if linkedin else 0
        hook_score     = 100 if hook and len(hook) > 20 else 0

        ai_keywords = ["python", "pytorch", "tensorflow", "ml", "ai", "nlp", "llm", "data science", "machine learning"]
        tech_score  = min(sum(1 for k in ai_keywords if any(k in t for t in tech_stack)) * 20, 100) if tech_stack else 0

        final_score = round(
            seniority_score  * weights.get("seniority",      0.25) +
            stage_score      * weights.get("company_stage",  0.20) +
            location_score   * weights.get("location_match", 0.10) +
            email_score      * weights.get("has_email",      0.15) +
            linkedin_score   * weights.get("has_linkedin",   0.10) +
            hook_score       * weights.get("has_hook",       0.10) +
            tech_score       * weights.get("tech_stack",     0.05) +
            confidence       * weights.get("confidence",     0.05), 1
        )

        scored.append({
            **p,
            "final_score": final_score,
            "score_breakdown": {
                "seniority":  round(seniority_score  * weights.get("seniority",      0.25), 1),
                "stage":      round(stage_score      * weights.get("company_stage",  0.20), 1),
                "location":   round(location_score   * weights.get("location_match", 0.10), 1),
                "email":      round(email_score      * weights.get("has_email",      0.15), 1),
                "linkedin":   round(linkedin_score   * weights.get("has_linkedin",   0.10), 1),
                "hook":       round(hook_score       * weights.get("has_hook",       0.10), 1),
                "tech":       round(tech_score       * weights.get("tech_stack",     0.05), 1),
                "confidence": round(confidence       * weights.get("confidence",     0.05), 1),
            },
            "company_funding": funding_stage,
            "pain_points":     pain_points
        })

    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    _log(logs, "success", f"Scored {len(scored)} leads")
    return {**state, "scored_leads": scored, "step": "scoring_done", "logs": logs}