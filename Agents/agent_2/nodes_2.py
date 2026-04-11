import re
import json
import requests
from core.state import AgentState
from core.llm import llm
from core.config import SERPER_API_KEY


def _parse_llm_json(raw: str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)

def _log(logs: list, level: str, msg: str):
    logs.append({"level": level, "msg": msg})


# NODE 1 — Decide WHO to find
def decide_targets_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])
    intent    = state.get("intent", {})
    logs      = []

    if not companies:
        return {**state, "error": "No companies to find people at.", "step": "targets_failed", "logs": logs}

    prompt = f"""
You are a B2B lead generation strategist.
User context:
  Role/Domain      : {intent.get('role')}
  Opportunity Type : {intent.get('opportunity_type')}
  Location         : {intent.get('location')}
  Work Mode        : {intent.get('work_mode')}
  Experience Level : {intent.get('experience_level')}

Return ONLY raw JSON. No markdown. Start with {{ and end with }}.
{{
  "primary_titles": ["Founder", "CTO", "VP Engineering"],
  "secondary_titles": ["Engineering Manager", "Tech Lead"],
  "search_intent": "One sentence explaining WHO and WHY",
  "linkedin_keywords": ["keywords for search"]
}}
Rules: max 4 primary, 4 secondary. Generic enough to match LinkedIn titles.
"""
    try:
        raw     = llm.invoke(prompt).content.strip()
        targets = _parse_llm_json(raw)
        _log(logs, "success", f"Targets decided: {', '.join(targets.get('primary_titles', []))}")
        return {**state, "target_personas": targets, "step": "targets_decided", "logs": logs}
    except Exception as e:
        _log(logs, "error", f"Target decision failed: {e}")
        return {**state, "error": str(e), "step": "targets_failed", "logs": logs}


# NODE 2 — Search People
def search_people_node(state: AgentState) -> AgentState:
    companies        = state.get("companies", [])
    personas         = state.get("target_personas", {})
    intent           = state.get("intent", {})
    logs             = []
    primary_titles   = personas.get("primary_titles", ["Founder", "CTO"])
    secondary_titles = personas.get("secondary_titles", ["Engineering Manager"])
    location         = intent.get("location", "")
    loc_str          = "" if location == "any" else location

    raw_results = []
    headers     = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    searched    = set()

    for company in companies:
        name = company.get("name", "")
        for title in (primary_titles[:2] + secondary_titles[:1]):
            combo = f"{name}_{title}"
            if combo in searched:
                continue
            searched.add(combo)

            queries = [
                f'site:linkedin.com/in "{name}" "{title}"',
                f'"{name}" founder OR CEO OR CTO linkedin.com/in',
                f'"{name}" team site:wellfound.com OR site:crunchbase.com',
            ]

            got_hits = False
            for query in queries:
                try:
                    resp    = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query.strip(), "num": 5})
                    results = resp.json().get("organic", [])
                    if results:
                        for r in results:
                            raw_results.append({
                                "company": name, "source": "serper",
                                "name": "", "title": r.get("title", ""),
                                "snippet": r.get("snippet", ""), "link": r.get("link", ""),
                                "confidence": 40
                            })
                        _log(logs, "info", f"{name} [{title}]: {len(results)} hits")
                        got_hits = True
                        break
                except Exception as e:
                    _log(logs, "warning", f"{name} [{title}] failed: {e}")

            if not got_hits:
                _log(logs, "info", f"{name} [{title}]: 0 hits")

    if not raw_results:
        return {**state, "error": "No people found.", "step": "people_search_failed", "logs": logs}

    _log(logs, "success", f"Total snippets collected: {len(raw_results)}")
    return {**state, "raw_people_results": raw_results, "step": "people_search_done", "logs": logs}


# NODE 3 — Extract People
def extract_people_node(state: AgentState) -> AgentState:
    raw_results = state.get("raw_people_results", [])
    personas    = state.get("target_personas", {})
    logs        = []

    if not raw_results:
        return {**state, "error": "No raw results to extract from.", "step": "extraction_failed", "logs": logs}

    serper_results   = [r for r in raw_results if r.get("source") == "serper"]
    extracted_people = []

    by_company = {}
    for r in serper_results:
        co = r.get("company", "Unknown")
        by_company.setdefault(co, []).append(
            f"Title: {r.get('title','')} | Snippet: {r.get('snippet','')} | Link: {r.get('link','')}"
        )

    for company_name, snippets in by_company.items():
        search_text = "\n".join(snippets[:10])
        prompt = f"""
You are a B2B lead extraction specialist.
Extract REAL people at "{company_name}".
Primary: {', '.join(personas.get('primary_titles', []))}
Secondary: {', '.join(personas.get('secondary_titles', []))}

Return ONLY raw JSON array. Start with [ end with ]. Return [] if none found.
[
  {{
    "company": "{company_name}",
    "source": "serper",
    "name": "Full name",
    "title": "Job title",
    "email": "email or empty",
    "linkedin_url": "LinkedIn URL or empty",
    "location": "City, Country or empty",
    "seniority": "c_suite | vp | director | manager | individual_contributor",
    "persona_type": "primary | secondary",
    "confidence": 50,
    "relevance_note": "Why relevant"
  }}
]
Rules: confidence >= 45, /in/ URLs only, don't invent names.
Search data:
{search_text}
"""
        try:
            raw    = llm.invoke(prompt).content.strip()
            people = _parse_llm_json(raw)
            if isinstance(people, list):
                extracted_people.extend(people)
                _log(logs, "info", f"{company_name}: {len(people)} people extracted")
        except Exception as e:
            _log(logs, "warning", f"Extraction failed for {company_name}: {e}")

    if not extracted_people:
        return {**state, "error": "No people extracted.", "step": "extraction_failed", "logs": logs}

    _log(logs, "success", f"Total people discovered: {len(extracted_people)}")
    return {**state, "discovered_people": extracted_people, "step": "people_extracted", "logs": logs}