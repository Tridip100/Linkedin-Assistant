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
    enriched_people: list        # people + about, expertise, best_hook, email_hint
    enriched_companies: list     # companies + funding, team_size, pain_points

    # ── Agent 4: Scoring (coming) ──
    scored_leads: list           # people ranked by fit score

    # ── Agent 5: Targeting (coming) ──
    target_list: list            # final filtered shortlist

    # ── Agent 6: Message Generator (coming) ──
    generated_messages: list     # personalized outreach per person

    # ── Global control ──
    messages: list
    error: Optional[str]
    step: str