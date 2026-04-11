import re
import json
import requests
from core.state import AgentState
from core.llm import llm
from core.config import SERPER_API_KEY


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _parse_llm_json(raw: str):
    """Strip markdown fences and parse JSON from LLM output."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


def _rule_based_intent(query: str) -> dict:
    """Fallback intent extractor when LLM is unavailable."""
    tokens = query.lower().split()
    return {
        "role": query,
        "opportunity_type": (
            "internship" if any(t in tokens for t in ["intern", "internship"]) else "any"
        ),
        "location": next(
            (t.capitalize() for t in tokens if t in [
                "india", "bangalore", "mumbai", "delhi", "hyderabad",
                "pune", "chennai", "kolkata", "remote"
            ]), "any"
        ),
        "work_mode": (
            "remote"  if "remote"  in tokens else
            "hybrid"  if "hybrid"  in tokens else
            "onsite"  if "onsite"  in tokens else "any"
        ),
        "experience_level": "fresher",
        "keywords": tokens,
    }


def _section(title: str):
    width = 62
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def _row(label: str, value: str):
    print(f"  {label:<18} {value}")


# ──────────────────────────────────────────────────────────────
# NODE 1 — Query Understanding
# ──────────────────────────────────────────────────────────────

def domain_input_node(state: AgentState) -> AgentState:
    domain = state.get("domain") or input(
        "\nWhat are you looking for?\n"
        "  e.g. 'ML internships India remote'  /  'backend jobs Bangalore hybrid'\n"
        "  > "
    ).strip()

    intent_prompt = f"""
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
        raw = llm.invoke(intent_prompt).content.strip()
        intent = _parse_llm_json(raw)
        _section("Search Intent")
        _row("Role",     intent.get("role", "—"))
        _row("Type",     intent.get("opportunity_type", "—"))
        _row("Location", intent.get("location", "—"))
        _row("Mode",     intent.get("work_mode", "—"))
        _row("Level",    intent.get("experience_level", "—"))
    except Exception as e:
        print(f"\n  [Warning] Intent parsing unavailable ({e}). Using query directly.")
        intent = _rule_based_intent(domain)

    return {**state, "domain": domain, "intent": intent, "step": "domain_captured"}


# ──────────────────────────────────────────────────────────────
# NODE 2 — Web Search
# ──────────────────────────────────────────────────────────────

def search_context_node(state: AgentState) -> AgentState:
    intent    = state.get("intent", {})
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

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    all_results = []

    print()
    for q in queries:
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": q.strip(), "num": 10},
            )
            results = resp.json().get("organic", [])
            all_results.extend(results)
            print(f"  Searched: {q.strip()[:65]}  ({len(results)} results)")
        except Exception as e:
            print(f"  [Warning] Search failed: {e}")

    if not all_results:
        return {**state, "error": "All searches returned no results.", "step": "context_failed"}

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

    if not raw_text.strip():
        return {**state, "error": "Search results contained no usable content.", "step": "context_failed"}

    print(f"\n  {len(unique)} unique results collected.")
    return {**state, "raw_text": raw_text, "step": "context_fetched"}


# ──────────────────────────────────────────────────────────────
# NODE 3 — Company Extraction
# ──────────────────────────────────────────────────────────────

def company_extraction_node(state: AgentState) -> AgentState:
    raw_text = state.get("raw_text", "")
    intent   = state.get("intent", {})

    if not raw_text.strip():
        return {**state, "error": "No search context available.", "step": "extraction_failed"}

    prompt = f"""
You are an expert career advisor and hiring intelligence system.

The user is looking for:
  Role              : {intent.get('role')}
  Opportunity Type  : {intent.get('opportunity_type')}
  Location          : {intent.get('location')}
  Work Mode         : {intent.get('work_mode')}
  Experience Level  : {intent.get('experience_level')}

From the search data below, extract the BEST SUITED companies for this user.

Selection criteria:
  - Actively hiring for the specified role/domain
  - Matches opportunity type (internship/full-time/etc.)
  - Matches work mode if specified
  - Suitable for the experience level
  - Prefer startups and mid-size companies
  - Must have a real hiring signal

Return ONLY a raw JSON array. No markdown. No explanation. Start with [ and end with ].

[
  {{
    "name": "Company name",
    "tagline": "One-line description of what the company does",
    "why_fit": "Specific reason this company suits the user's query",
    "roles": ["Role 1", "Role 2"],
    "opportunity_type": "internship | full-time | contract",
    "work_mode": "remote | hybrid | onsite",
    "location": "City, Country or Remote",
    "salary_range": "Range or stipend amount",
    "experience_required": "Fresher | 0-1 yr | 1-3 yrs",
    "tech_stack": ["Python", "TensorFlow"],
    "hiring_signal": "Source of hiring info",
    "apply_link": "Direct URL or empty string",
    "fit_score": 85
  }}
]

Rules:
  - fit_score is 0-100 based on match quality
  - Sort by fit_score descending
  - Return 5-8 companies, only those with fit_score >= 60

Search data:
{raw_text}
"""

    raw_response = ""
    try:
        raw_response = llm.invoke(prompt).content.strip()
        companies = _parse_llm_json(raw_response)

        if not isinstance(companies, list) or len(companies) == 0:
            raise ValueError("LLM returned an empty or invalid list.")

        return {**state, "companies": companies, "step": "companies_extracted"}

    except Exception as e:
        print(f"\n  [Error] Company extraction failed: {e}")
        return {**state, "error": str(e), "step": "extraction_failed"}


# ──────────────────────────────────────────────────────────────
# NODE 4 — Display Results
# ──────────────────────────────────────────────────────────────

def display_companies_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])

    if not companies:
        print("\n  No suitable companies found. Try a broader query.")
        return {**state, "step": "no_companies"}

    intent = state.get("intent", {})
    _section(
        f"Results: {intent.get('role')} — {intent.get('opportunity_type').title()} "
        f"| {intent.get('location')} | {intent.get('work_mode').title()}"
    )

    for i, c in enumerate(companies, 1):
        score = c.get("fit_score", 0)
        bar   = ("█" * (score // 10) + "░" * (10 - score // 10)) if isinstance(score, int) else ""

        print(f"\n  [{i}] {c.get('name')}   {bar} {score}/100")
        print(f"      {c.get('tagline', '—')}")
        print()
        _row("Why a fit",   c.get("why_fit", "—"))
        _row("Roles",       ", ".join(c.get("roles", [])))
        _row("Type",        f"{c.get('opportunity_type','—')}  |  {c.get('work_mode','—')}")
        _row("Location",    c.get("location", "—"))
        _row("Package",     c.get("salary_range", "Not disclosed"))
        _row("Level",       c.get("experience_required", "—"))
        _row("Stack",       ", ".join(c.get("tech_stack", [])))
        _row("Signal",      c.get("hiring_signal", "—"))
        if c.get("apply_link"):
            _row("Apply",   c.get("apply_link"))

    return {**state, "step": "companies_displayed"}


# ──────────────────────────────────────────────────────────────
# NODE 5 — User Selection
# ──────────────────────────────────────────────────────────────

def user_selection_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])

    if not companies:
        return {**state, "error": "No companies to select from.", "step": "selection_failed"}

    try:
        raw = input("\n  Enter company number for a detailed breakdown: ").strip()
        choice = int(raw) - 1

        if choice < 0 or choice >= len(companies):
            raise IndexError

        selected = companies[choice]
        print(f"\n  Selected: {selected.get('name')}")
        return {**state, "selected_company": selected, "step": "company_selected"}

    except ValueError:
        print("  Invalid input. Please enter a number.")
        return {**state, "error": "Invalid input.", "step": "selection_failed"}
    except IndexError:
        print("  Selection out of range.")
        return {**state, "error": "Selection out of range.", "step": "selection_failed"}


# ──────────────────────────────────────────────────────────────
# NODE 6 — Deep Company Insights
# ──────────────────────────────────────────────────────────────

def company_info_node(state: AgentState) -> AgentState:
    company = state.get("selected_company")
    intent  = state.get("intent", {})

    if not company or not company.get("name"):
        return {**state, "error": "Invalid company data.", "step": "company_info_failed"}

    prompt = f"""
You are a career strategist helping a job seeker.

The user is a {intent.get('experience_level', 'fresher')} seeking 
{intent.get('opportunity_type', 'a position')} in {intent.get('role', 'tech')}.

Company   : {company.get('name')}
About     : {company.get('tagline')}
Roles     : {', '.join(company.get('roles', []))}
Stack     : {', '.join(company.get('tech_stack', []))}
Package   : {company.get('salary_range')}

Return ONLY a raw JSON object. No markdown. No explanation. Start with {{ and end with }}.

{{
  "company_summary": ["2-3 concise insights about culture and growth"],
  "why_join": ["Top 3 career reasons to join this company"],
  "top_roles": ["Top 5 open or likely-open roles"],
  "must_have_skills": ["Skills to highlight in your application"],
  "preparation_tips": ["What to prepare for their hiring process"],
  "recent_signals": ["Recent funding, product launches, or hiring news"],
  "linkedin_message": "A short, human-sounding cold outreach message for a recruiter or founder. Under 300 characters. No AI clichés.",
  "email_template": "Subject line + cold email body. Max 150 words. Mention the role and your fit directly."
}}
"""

    raw_response = ""
    try:
        raw_response = llm.invoke(prompt).content.strip()
        insights = _parse_llm_json(raw_response)

        _section(f"Company Breakdown: {company.get('name')}")

        print("\n  About")
        for s in insights.get("company_summary", []):
            print(f"    - {s}")

        print("\n  Why Join")
        for r in insights.get("why_join", []):
            print(f"    - {r}")

        print("\n  Open Roles")
        for role in insights.get("top_roles", []):
            print(f"    - {role}")

        print("\n  Must-Have Skills")
        for skill in insights.get("must_have_skills", []):
            print(f"    - {skill}")

        print("\n  How to Prepare")
        for tip in insights.get("preparation_tips", []):
            print(f"    - {tip}")

        print("\n  Recent Activity")
        for signal in insights.get("recent_signals", []):
            print(f"    - {signal}")

        print("\n  LinkedIn Message")
        print(f"    {insights.get('linkedin_message', '—')}")

        print("\n  Email Template")
        print(f"{insights.get('email_template', '—')}")

        return {**state, "company_insights": insights, "step": "company_insights_generated"}

    except Exception as e:
        print(f"\n  [Error] Could not generate company insights: {e}")
        return {**state, "error": str(e), "step": "company_info_failed"}