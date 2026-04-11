from typing import TypedDict, Optional

class AgentState(TypedDict):
    # Agent 1
    domain: str
    intent: dict
    raw_text: str
    companies: list
    selected_company: Optional[dict]
    company_insights: Optional[dict]

    # Agent 2
    target_personas: dict
    raw_people_results: list
    discovered_people: list

    # Agent 3
    enriched_people: list
    enriched_companies: list

    # Agent 4
    interview_questions: list    # ← NEW: generated questions for frontend
    human_answers: dict
    scoring_config: dict
    scored_leads: list

    # Agent 5
    target_list: list
    dashboard_stats: dict        # ← NEW: pre-Agent6 dashboard data

    # Agent 6
    sender_profile: dict
    generated_messages: list
    campaign_plan: dict

    # Global
    logs: list                   # ← NEW: all logs from all agents
    messages: list
    error: Optional[str]
    step: str