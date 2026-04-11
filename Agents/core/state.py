from typing import TypedDict, Optional

class AgentState(TypedDict):

    # ── Agent 1: Company Discovery ──
    domain: str
    intent: dict
    raw_text: str
    companies: list
    selected_company: Optional[dict]
    company_insights: Optional[dict]

    # ── Agent 2: People Finder ──
    target_personas: dict
    raw_people_results: list
    discovered_people: list

    # ── Agent 3: Enrichment ──
    enriched_people: list
    enriched_companies: list

    # ── Agent 4: Scoring ──
    scored_leads: list
    scoring_config: dict
    human_answers: dict

    # ── Agent 5: Targeting ──
    target_list: list

    # ── Agent 6: Message Generator (coming) ──
    generated_messages: list

    # ── Global control ──
    messages: list
    error: Optional[str]
    step: str