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

def _rule_based_intent(query: str) -> dict:
    tokens = query.lower().split()
    return {
        "role": query,
        "opportunity_type": "internship" if any(t in tokens for t in ["intern", "internship"]) else "any",
        "location": next((t.capitalize() for t in tokens if t in [
            "india", "bangalore", "mumbai", "delhi", "hyderabad",
            "pune", "chennai", "kolkata", "remote"
        ]), "any"),
        "work_mode": "remote" if "remote" in tokens else "hybrid" if "hybrid" in tokens else "onsite" if "onsite" in tokens else "any",
        "experience_level": "fresher",
        "keywords": tokens,
    }


def domain_input_node(state: AgentState) -> AgentState:
    domain = state.get("domain", "").strip()
    logs   = []

    if not domain:
        return {**state, "error": "No search query provided.", "step": "domain_failed", "logs": logs}

    prompt = f"""
You are a job search intent parser.
User query: "{domain}"
Extract structured intent. Return ONLY valid JSON — no markdown, no explanation.
{{
  "role": "the job role or skill domain",
  "opportunity_type": "internship | full-time | part-time | contract | any",
  "location": "city/country/region, or 'any'",
  "work_mode": "remote | onsite | hybrid | any",
  "experience_level": "fresher | student | 0-2 years | experienced | any",
  "keywords": ["relevant", "search", "keywords"]
}}
"""
    try:
        raw    = llm.invoke(prompt).content.strip()
        intent = _parse_llm_json(raw)
        _log(logs, "success", f"Intent: {intent.get('role')} | {intent.get('opportunity_type')} | {intent.get('location')}")
    except Exception as e:
        intent = _rule_based_intent(domain)
        _log(logs, "warning", f"Fallback intent used: {e}")

    return {**state, "domain": domain, "intent": intent, "step": "domain_captured", "logs": logs}


def search_context_node(state: AgentState) -> AgentState:
    intent    = state.get("intent", {})
    logs      = []
    role      = intent.get("role", state.get("domain", ""))
    opp_type  = intent.get("opportunity_type", "any")
    location  = intent.get("location", "any")
    work_mode = intent.get("work_mode", "any")

    opp  = "" if opp_type  == "any" else opp_type
    loc  = "" if location  == "any" else location
    mode = "" if work_mode == "any" else work_mode

    queries = [
        f"{role} {opp} {loc} {mode} hiring startups site:linkedin.com OR site:wellfound.com",
        f"{role} {opp} {loc} companies hiring 2024 2025",
        f"best startups hiring {role} {opp} {mode} {loc}",
    ]

    headers     = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    all_results = []

    for q in queries:
        try:
            resp    = requests.post("https://google.serper.dev/search", headers=headers, json={"q": q.strip(), "num": 10})
            results = resp.json().get("organic", [])
            all_results.extend(results)
            _log(logs, "info", f"Searched: {q.strip()[:60]} ({len(results)} results)")
        except Exception as e:
            _log(logs, "warning", f"Search failed: {e}")

    if not all_results:
        return {**state, "error": "All searches returned no results.", "step": "context_failed", "logs": logs}

    seen, unique = set(), []
    for r in all_results:
        link = r.get("link", "")
        if link not in seen:
            seen.add(link)
            unique.append(r)

    raw_text = "\n".join(
        f"Title: {r.get('title','')} | Snippet: {r.get('snippet','')} | Link: {r.get('link','')}"
        for r in unique
    )

    _log(logs, "success", f"{len(unique)} unique results collected")
    return {**state, "raw_text": raw_text, "step": "context_fetched", "logs": logs}


def company_extraction_node(state: AgentState) -> AgentState:
    raw_text = state.get("raw_text", "")
    intent   = state.get("intent", {})
    logs     = []

    if not raw_text.strip():
        return {**state, "error": "No search context available.", "step": "extraction_failed", "logs": logs}

    prompt = f"""
You are an expert career advisor and hiring intelligence system.
The user is looking for:
  Role              : {intent.get('role')}
  Opportunity Type  : {intent.get('opportunity_type')}
  Location          : {intent.get('location')}
  Work Mode         : {intent.get('work_mode')}
  Experience Level  : {intent.get('experience_level')}

From the search data below, extract the BEST SUITED companies.
Return ONLY a raw JSON array. No markdown. Start with [ and end with ].

[
  {{
    "name": "Company name",
    "tagline": "One-line description",
    "why_fit": "Specific reason this suits the user",
    "roles": ["Role 1", "Role 2"],
    "opportunity_type": "internship | full-time | contract",
    "work_mode": "remote | hybrid | onsite",
    "location": "City, Country or Remote",
    "salary_range": "Range or stipend",
    "experience_required": "Fresher | 0-1 yr | 1-3 yrs",
    "tech_stack": ["Python", "TensorFlow"],
    "hiring_signal": "Source of hiring info",
    "apply_link": "Direct URL or empty string",
    "website_domain": "company.com or empty string",
    "fit_score": 85
  }}
]

Rules: fit_score 0-100, sort descending, only >= 60, return 5-8 companies.
Search data:
{raw_text}
"""
    try:
        raw_response = llm.invoke(prompt).content.strip()
        companies    = _parse_llm_json(raw_response)

        if not isinstance(companies, list) or len(companies) == 0:
            raise ValueError("LLM returned empty list")

        _log(logs, "success", f"{len(companies)} companies extracted")
        return {**state, "companies": companies, "step": "companies_extracted", "logs": logs}

    except Exception as e:
        _log(logs, "error", f"Company extraction failed: {e}")
        return {**state, "error": str(e), "step": "extraction_failed", "logs": logs}


def company_info_node(state: AgentState) -> AgentState:
    company = state.get("selected_company")
    intent  = state.get("intent", {})
    logs    = []

    if not company or not company.get("name"):
        return {**state, "error": "Invalid company data.", "step": "company_info_failed", "logs": logs}

    prompt = f"""
You are a career strategist.
User: {intent.get('experience_level', 'fresher')} seeking {intent.get('opportunity_type')} in {intent.get('role')}.
Company: {company.get('name')}, About: {company.get('tagline')}
Roles: {', '.join(company.get('roles', []))}, Stack: {', '.join(company.get('tech_stack', []))}

Return ONLY raw JSON. Start with {{ end with }}.
{{
  "company_summary": ["2-3 insights"],
  "why_join": ["Top 3 reasons"],
  "top_roles": ["Top 5 roles"],
  "must_have_skills": ["Key skills"],
  "preparation_tips": ["Prep tips"],
  "recent_signals": ["Recent news"],
  "linkedin_message": "Under 300 chars outreach",
  "email_template": "Subject + body max 150 words"
}}
"""
    try:
        raw_response = llm.invoke(prompt).content.strip()
        insights     = _parse_llm_json(raw_response)
        _log(logs, "success", f"Insights generated for {company.get('name')}")
        return {**state, "company_insights": insights, "step": "company_insights_generated", "logs": logs}
    except Exception as e:
        _log(logs, "error", f"Company insights failed: {e}")
        return {**state, "error": str(e), "step": "company_info_failed", "logs": logs}