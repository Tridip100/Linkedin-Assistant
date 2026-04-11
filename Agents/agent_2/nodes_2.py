import re
import json
import requests
from urllib.parse import urlparse
from core.state import AgentState
from core.llm import llm
from core.config import SERPER_API_KEY,MISTRAL_API_KEY


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _parse_llm_json(raw: str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


def _section(title: str):
    width = 62
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def _row(label: str, value: str):
    print(f"  {label:<22} {value}")


# ──────────────────────────────────────────────────────────────
# NODE 1 — Decide WHO to find per company
# ──────────────────────────────────────────────────────────────

def decide_targets_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])
    intent    = state.get("intent", {})

    if not companies:
        return {**state, "error": "No companies to find people at.", "step": "targets_failed"}

    prompt = f"""
You are a B2B lead generation strategist.

The user's goal context:
  Role/Domain      : {intent.get('role')}
  Opportunity Type : {intent.get('opportunity_type')}
  Location         : {intent.get('location')}
  Work Mode        : {intent.get('work_mode')}
  Experience Level : {intent.get('experience_level')}

Based on this context, decide the BEST person titles to target at a company.

Return ONLY raw JSON. No markdown. Start with {{ and end with }}.

{{
  "primary_titles": ["e.g. Founder", "CTO", "VP Engineering"],
  "secondary_titles": ["e.g. Engineering Manager", "Tech Lead", "HR Manager"],
  "search_intent": "One sentence explaining WHO and WHY we are targeting them",
  "linkedin_keywords": ["keywords to use in LinkedIn people search"]
}}

Rules:
- primary_titles = decision makers who can directly act
- secondary_titles = influencers who can refer or forward
- Keep titles generic enough to match real LinkedIn/Apollo titles
- Return max 4 primary and 4 secondary titles
"""

    try:
        raw     = llm.invoke(prompt).content.strip()
        targets = _parse_llm_json(raw)

        _section("Target Personas")
        print(f"\n  Intent    : {targets.get('search_intent')}")
        print(f"\n  Primary   : {', '.join(targets.get('primary_titles', []))}")
        print(f"  Secondary : {', '.join(targets.get('secondary_titles', []))}")

        return {**state, "target_personas": targets, "step": "targets_decided"}

    except Exception as e:
        print(f"\n  [Error] Target decision failed: {e}")
        return {**state, "error": str(e), "step": "targets_failed"
        }

# ──────────────────────────────────────────────────────────────
# NODE 2 — Apollo.io People Search (primary)
#          Serper fallback if Apollo returns nothing
# ──────────────────────────────────────────────────────────────
def search_people_node(state: AgentState) -> AgentState:
    companies  = state.get("companies", [])
    personas   = state.get("target_personas", {})
    intent     = state.get("intent", {})

    primary_titles   = personas.get("primary_titles", ["Founder", "CTO"])
    secondary_titles = personas.get("secondary_titles", ["Engineering Manager"])
    location         = intent.get("location", "")
    loc_str          = "" if location == "any" else location

    raw_results = []
    headers     = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    searched    = set()   # ← track already searched company+title combos

    _section("People Search")

    for company in companies:
        name = company.get("name", "")

        for title in (primary_titles[:2] + secondary_titles[:1]):
            combo = f"{name}_{title}"
            if combo in searched:        # ← skip duplicates
                continue
            searched.add(combo)

            # Query priority order — most specific to broadest
            queries = [
                f'site:linkedin.com/in "{name}" "{title}"',
                f'"{name}" founder OR CEO OR CTO linkedin.com/in',
                f'"{name}" team site:wellfound.com OR site:crunchbase.com',
            ]

            got_hits = False
            for query in queries:
                try:
                    resp = requests.post(
                        "https://google.serper.dev/search",
                        headers=headers,
                        json={"q": query.strip(), "num": 5}
                    )
                    results = resp.json().get("organic", [])

                    if results:
                        for r in results:
                            raw_results.append({
                                "company":  name,
                                "source":   "serper",
                                "name":     "",
                                "title":    r.get("title", ""),
                                "snippet":  r.get("snippet", ""),
                                "link":     r.get("link", ""),
                                "confidence": 40
                            })
                        print(f"  {name:<30} → {len(results)} hits [{title}] ✓")
                        got_hits = True
                        break   # stop trying other queries

                except Exception as e:
                    print(f"  [Warning] {name} [{title}]: {e}")

            if not got_hits:
                print(f"  {name:<30} → 0 hits [{title}]")

    if not raw_results:
        return {**state, "error": "No people found.", "step": "people_search_failed"}

    print(f"\n  Total snippets collected: {len(raw_results)}")
    return {**state, "raw_people_results": raw_results, "step": "people_search_done"}

# ──────────────────────────────────────────────────────────────
# NODE 3 — Extract & Structure People
# ──────────────────────────────────────────────────────────────

def extract_people_node(state: AgentState) -> AgentState:
    raw_results = state.get("raw_people_results", [])
    personas    = state.get("target_personas", {})

    if not raw_results:
        return {**state, "error": "No raw people results to extract from.",
                "step": "extraction_failed"}

    # Apollo results are already structured — pass them through directly
    apollo_people = [r for r in raw_results if r.get("source") == "apollo"]

    # Serper results need LLM extraction — group by company
    serper_results = [r for r in raw_results if r.get("source") == "serper"]

    extracted_people = list(apollo_people)  # start with clean Apollo data

    # LLM extraction only for Serper snippets
    if serper_results:
        by_company = {}
        for r in serper_results:
            co = r.get("company", "Unknown")
            by_company.setdefault(co, []).append(
                f"Title: {r.get('title','')} | "
                f"Snippet: {r.get('snippet','')} | "
                f"Link: {r.get('link','')}"
            )

        for company_name, snippets in by_company.items():
            search_text = "\n".join(snippets[:10])

            prompt = f"""
You are a B2B lead extraction specialist.

From the search results below, extract REAL people at "{company_name}".

Target personas:
  Primary   : {', '.join(personas.get('primary_titles', []))}
  Secondary : {', '.join(personas.get('secondary_titles', []))}

Return ONLY a raw JSON array. No markdown. Start with [ and end with ].
Return [] if no real people found.

[
  {{
    "company": "{company_name}",
    "source": "serper",
    "name": "Full name or empty string",
    "title": "Job title",
    "email": "email if found else empty string",
    "linkedin_url": "LinkedIn URL if found else empty string",
    "location": "City, Country or empty string",
    "seniority": "c_suite | vp | director | manager | individual_contributor",
    "persona_type": "primary | secondary",
    "confidence": 50,
    "relevance_note": "One line why this person is relevant"
  }}
]

Rules:
  - Include people with confidence >= 45
  - If the snippet title contains the company name → confidence 80+
  - If LinkedIn URL is present → confidence 70+
  - If only mentioned in snippet (not title) → confidence 50
  - Extract partial info — empty string for missing fields
  - A crunchbase/wellfound URL is still valid as linkedin_url field
  - Do NOT invent names — only extract from data

Search data:
{search_text}
"""
            try:
                raw    = llm.invoke(prompt).content.strip()
                people = _parse_llm_json(raw)
                if isinstance(people, list):
                    extracted_people.extend(people)
                    print(f"  {company_name} [Serper] → {len(people)} people extracted by LLM")
            except Exception as e:
                print(f"  [Error] LLM extraction failed for {company_name}: {e}")

    if not extracted_people:
        return {**state,
                "error": "No people could be extracted.",
                "step":  "extraction_failed"}

    print(f"\n  Total people discovered: {len(extracted_people)}")
    return {**state, "discovered_people": extracted_people, "step": "people_extracted"}


# ──────────────────────────────────────────────────────────────
# NODE 4 — Display Results
# ──────────────────────────────────────────────────────────────

def display_people_node(state: AgentState) -> AgentState:
    people = state.get("discovered_people", [])

    if not people:
        print("\n  No people found across all companies.")
        return {**state, "step": "no_people_found"}

    # Group by company
    by_company = {}
    for p in people:
        co = p.get("company", "Unknown")
        by_company.setdefault(co, []).append(p)

    _section(f"People Finder — {len(people)} contacts across {len(by_company)} companies")

    for co, persons in by_company.items():
        # Sort: primary first, then by confidence
        persons.sort(key=lambda x: (
            0 if x.get("persona_type") == "primary" else 1,
            -x.get("confidence", 0)
        ))

        print(f"\n  🏢 {co}")
        for p in persons:
            tag = "★ PRIMARY  " if p.get("persona_type") == "primary" else "· secondary"
            name = p.get("name") or "Unknown"
            print(f"\n    [{tag}]  {name}  —  {p.get('title', '—')}")
            if p.get("email"):
                _row("Email",      p.get("email"))
            if p.get("linkedin_url"):
                _row("LinkedIn",   p.get("linkedin_url"))
            if p.get("location"):
                _row("Location",   p.get("location"))
            if p.get("seniority"):
                _row("Seniority",  p.get("seniority"))
            _row("Source",         p.get("source", "—").upper())
            _row("Confidence",     f"{p.get('confidence', '—')}/100")
            if p.get("relevance_note"):
                _row("Why",        p.get("relevance_note"))

    return {**state, "step": "people_displayed"}