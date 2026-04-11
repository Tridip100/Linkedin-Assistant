import re 
import json
import requests
from urllib.parse import urlparse
from core.llm import llm
from core.config import SERPER_API_KEY, APPOLO_API_KEY
from core.state import AgentState


def _parse_llm_json(raw:str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)

def _section(title: str):
    width = 62
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")

def _row(label: str, value: str):
    print(f"  {label:<25} {value}")

def _is_valid_profile_url(url:str) ->bool :
    """Check if Url is a real linkdin profile not a post"""
    if not url:
        return False
    return "/in" in url and "/posts/" not in url and "crunchbase" not in url 

#-----------------------------------------------------------------------------------
#Node 1 -Clean and fix problems
#--------------------------------------------------------------------------------------


def clean_profiles_node(state: AgentState) -> AgentState:
    """
    Fix bad LinkedIn URLs, fill missing names/titles,
    remove duplicates, filter out unknown persons.
    """

    people = state.get("discovered_people", [])

    if not people:
        return {**state, "error": "No people to enrich.", "step": "clean_failed"}

    _section("Cleaning & Validating Profiles")

    cleaned   = []
    seen_urls = set()

    # ── Keywords that indicate non-persons ──
    skip_keywords = ["demo", "test", "bot", "official", "page", 
                     "account", "team", "support", "admin", "info"]

    for p in people:
        name       = p.get("name", "").strip()
        title      = p.get("title", "").strip()
        linkedin   = p.get("linkedin_url", "").strip()
        company    = p.get("company", "")
        confidence = p.get("confidence", 0)

        # ── Skip empty or unknown names ──────────────────────
        if not name or name.lower() in ["unknown", "none", ""]:
            print(f"  ⚠ Skipped — no name [{company}]")
            continue

        # ── Skip non-persons ─────────────────────────────────
        if any(k in name.lower() for k in skip_keywords):
            print(f"  ⚠ Skipped — not a real person: {name}")
            continue

        # ── Fix /posts/ URLs ─────────────────────────────────
        if linkedin and not _is_valid_profile_url(linkedin):
            match = re.search(r"/posts/([a-zA-Z0-9\-]+)_", linkedin)
            if match:
                guessed = f"https://www.linkedin.com/in/{match.group(1)}"
                print(f"  🔧 Fixed URL: {linkedin[:50]} → {guessed}")
                linkedin = guessed
            else:
                linkedin = ""

        # ── Deduplicate by LinkedIn URL ──────────────────────
        if linkedin and linkedin in seen_urls:
            print(f"  ⚠ Duplicate skipped: {name}")
            continue
        if linkedin:
            seen_urls.add(linkedin)

        cleaned.append({
            **p,
            "name":         name,
            "title":        title,
            "linkedin_url": linkedin,
            "email":        "",
            "recent_posts": [],
            "enriched":     False
        })

    print(f"\n  Input  : {len(people)} people")
    print(f"  Output : {len(cleaned)} valid profiles after cleaning")

    return {**state, "discovered_people": cleaned, "step": "profiles_cleaned"}

#--------------------------------------------------------------
#Enrich People of Linkdin
#---------------------------------------------------------------------

def enrich_people_node(state: AgentState) -> AgentState:
    """
    For each person, search the web to get:
    - Confirmed current role
    - Recent LinkedIn posts / activity
    - Any public email or contact info
    - Interviews, talks, articles they've written
    """

    people  = state.get("discovered_people", [])
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    _section("Enriching People Profiles")

    enriched_people = []

    for p in people:
        name    = p.get("name", "")
        company = p.get("company", "")
        title   = p.get("title", "")

        queries = [
            f'"{name}" "{company}" linkedin',
            f'"{name}" {company} interview OR podcast OR talk OR article',
        ]

        all_snippets = []

        for query in queries:
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query.strip(), "num": 5}
                )
                results = resp.json().get("organic", [])
                all_snippets.extend([
                    {
                        "title":   r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "link":    r.get("link", "")
                    }
                    for r in results
                ])
            except Exception as e:
                print(f"  [Warning] Enrich search failed for {name}: {e}")

        if not all_snippets:
            enriched_people.append(p)
            print(f"  {name:<30} → no additional data found")
            continue
        snippets_text = "\n".join(
            f"Title: {s['title']} | Snippet: {s['snippet']} | Link: {s['link']}"
            for s in all_snippets[:10]
        )

        prompt = f"""
You are enriching a B2B contact profile.

Person    : {name}
Company   : {company}
Known Title: {title}

From the search data below, extract enrichment info.
Return ONLY raw JSON. No markdown. Start with {{ and end with }}.

{{
  "confirmed_title": "Most accurate current job title from data",
  "confirmed_company": "Confirmed company name",
  "linkedin_url": "LinkedIn /in/ URL if found, else empty string",
  "email_hint": "Any email found in snippets, else empty string",
  "location": "City, Country if found",
  "about": "1-2 sentence summary of who this person is",
  "recent_activity": ["recent post topic or article title (max 3)"],
  "expertise": ["key skills or topics they post about (max 4)"],
  "best_hook": "One specific thing to reference when reaching out to this person"
}}

Rules:
  - Only extract from the data — do not invent
  - confirmed_title should be their CURRENT role
  - best_hook = a recent post, project, achievement, or opinion they shared
  - If LinkedIn URL found must contain /in/ — reject /posts/ URLs

Search data:
{snippets_text}
"""

        try:
            raw      = llm.invoke(prompt).content.strip()
            enriched = _parse_llm_json(raw)

            # Merge enrichment into person dict
            updated = {
                **p,
                "title":           enriched.get("confirmed_title") or title,
                "company":         enriched.get("confirmed_company") or company,
                "linkedin_url":    enriched.get("linkedin_url") or p.get("linkedin_url", ""),
                "email_hint":      enriched.get("email_hint", ""),
                "location":        enriched.get("location") or p.get("location", ""),
                "about":           enriched.get("about", ""),
                "recent_activity": enriched.get("recent_activity", []),
                "expertise":       enriched.get("expertise", []),
                "best_hook":       enriched.get("best_hook", ""),
                "enriched":        True
            }

            enriched_people.append(updated)
            hook = enriched.get("best_hook", "")[:50]
            print(f"  {name:<30} → enriched ✓  hook: {hook}...")

        except Exception as e:
            print(f"  [Error] LLM enrichment failed for {name}: {e}")
            enriched_people.append(p)

    return {**state, "enriched_people": enriched_people, "step": "people_enriched"}


#--------------------------------------------------------------------------------------------
# Enrich Companies Node 
#-------------------------------------------------------------------------
def enrich_companies_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])
    headers   = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    _section("Enrich Company Profiles")

    enriched_companies = []

    for company in companies:
        name   = company.get("name", "")
        domain = company.get("website_domain", "")

        apollo_data = {}

        # ── Apollo first (free org enrich) ──────────────────
        if domain:
            try:
                resp = requests.get(
                    "https://api.apollo.io/v1/organizations/enrich",
                    params={
                        "api_key": APPOLO_API_KEY,
                        "domain":  domain
                    }
                )
                org = resp.json().get("organization", {})

                if org:
                    # Fix: Apollo returns tech as list of dicts
                    raw_stack  = org.get("technologies", [])
                    tech_stack = [
                        t.get("name", t) if isinstance(t, dict) else t
                        for t in raw_stack
                    ]

                    apollo_data = {
                        "funding_stage":    org.get("latest_funding_stage") or "Unknown",
                        "funding_amount":   str(org.get("total_funding")    or "Unknown"),
                        "team_size":        str(org.get("estimated_num_employees") or "Unknown"),
                        "tech_stack":       tech_stack,
                        "company_linkedin": org.get("linkedin_url", ""),
                        "website":          org.get("website_url", ""),
                        "growth_signal":    org.get("short_description", ""),
                        "industry":         org.get("industry", "")
                    }
                    print(f"  {name:<30} → Apollo ✓ | {apollo_data.get('funding_stage')} | {apollo_data.get('team_size')} employees")

            except Exception as e:
                print(f"  [Warning] Apollo failed for {name}: {e}")

        # ── Serper for news + pain points ───────────────────
        queries = [
            f'"{name}" funding OR raised OR series site:crunchbase.com OR site:techcrunch.com',
            f'"{name}" news OR launch OR product 2024 OR 2025',
        ]

        all_snippets = []
        for query in queries:
            try:
                resp = requests.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query.strip(), "num": 5}
                )
                results = resp.json().get("organic", [])
                all_snippets.extend([
                    {
                        "title":   r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "link":    r.get("link", "")
                    }
                    for r in results
                ])
            except Exception as e:
                print(f"  [Warning] Serper failed for {name}: {e}")

        # ── LLM extracts news + pain points ─────────────────
        serper_enriched = {}
        if all_snippets:
            snippets_text = "\n".join(
                f"Title: {s['title']} | Snippet: {s['snippet']}"
                for s in all_snippets[:10]
            )

            prompt = f"""
You are enriching a B2B company profile for lead generation.

Company        : {name}
Funding Stage  : {apollo_data.get('funding_stage', 'Unknown')}
Team Size      : {apollo_data.get('team_size', 'Unknown')}

From the search data extract ONLY recent news and pain points.
Return ONLY raw JSON. No markdown. Start with {{ and end with }}.

{{
  "recent_news"   : ["1-2 most recent notable events or launches"],
  "pain_points"   : ["1-2 business challenges they likely face"],
  "funding_stage" : "only fill if unknown above, else empty string",
  "funding_amount": "only fill if unknown above, else empty string"
}}

Search data:
{snippets_text}
"""
            try:
                raw             = llm.invoke(prompt).content.strip()
                serper_enriched = _parse_llm_json(raw)
            except Exception as e:
                print(f"  [Error] LLM enrichment failed for {name}: {e}")

        if not apollo_data and not serper_enriched:
            enriched_companies.append(company)
            print(f"  {name:<30} → no data found")
            continue

        # ── Merge Apollo + Serper ────────────────────────────
        updated = {
            **company,
            "funding_stage":    apollo_data.get("funding_stage")    or serper_enriched.get("funding_stage", "Unknown"),
            "funding_amount":   apollo_data.get("funding_amount")   or serper_enriched.get("funding_amount", "Unknown"),
            "team_size":        apollo_data.get("team_size")        or "Unknown",
            "tech_stack":       apollo_data.get("tech_stack")       or company.get("tech_stack", []),
            "company_linkedin": apollo_data.get("company_linkedin") or "",
            "website":          apollo_data.get("website")          or "",
            "growth_signal":    apollo_data.get("growth_signal")    or "",
            "industry":         apollo_data.get("industry")         or "",
            "recent_news":      serper_enriched.get("recent_news",  []),
            "pain_points":      serper_enriched.get("pain_points",  []),
            "apollo_enriched":  bool(apollo_data)
        }

        enriched_companies.append(updated)  # ← only append ONCE (you had it twice before)
        print(f"  {name:<30} → {updated.get('funding_stage')} | {updated.get('team_size')} people | {updated.get('funding_amount')}")

    print(f"\n  Apollo enriched : {sum(1 for c in enriched_companies if c.get('apollo_enriched'))}/{len(enriched_companies)} companies")
    return {**state, "enriched_companies": enriched_companies, "step": "companies_enriched"}

#---------------------------------------------------------------------
# Email Guess Node
#---------------------------------------------------------------------------------------
def email_guess_node(state: AgentState) -> AgentState:
    """
    Generate probable email addresses from name + company domain.
    Common patterns: firstname@company.com, f.lastname@company.com
    Uses enriched company website domain.
    """
    people = state.get("enriched_people", [])

   
    enriched_companies = state.get("enriched_companies", [])

    domain_map = {}
    for c in enriched_companies:
        name    = c.get("name", "")
        website = c.get("website", "")
        if website:
            parsed = urlparse(website)
            domain = parsed.netloc.replace("www.", "")
            if domain:
                domain_map[name] = domain

    _section("Email Pattern Generation")

    updated_people = []

    for p in people:
        name        = p.get("name", "")
        company     = p.get("company", "")
        email_hint  = p.get("email_hint", "")

        if email_hint and "@" in email_hint:
            updated_people.append(p)
            print(f"  {name:<30} → {email_hint} (found)")
            continue

        domain = domain_map.get(company, "")

        if not domain or not name:
            updated_people.append(p)
            print(f"  {name:<30} → no domain available")
            continue

        parts      = name.lower().split()
        first      = parts[0] if parts else ""
        last       = parts[-1] if len(parts) > 1 else ""
        
        patterns = []
        if first and last:
            patterns = [
                f"{first}@{domain}",
                f"{first}.{last}@{domain}",
                f"{first[0]}{last}@{domain}",
                f"{first}_{last}@{domain}",
            ]
        elif first:
            patterns = [f"{first}@{domain}"]

        updated_people.append({
            **p,
            "email_patterns": patterns,
            "email_hint":     patterns[0] if patterns else ""
        })

        print(f"  {name:<30} → {patterns[0] if patterns else 'could not generate'}")

    return {**state, "enriched_people": updated_people, "step": "emails_guessed"}

#----------------------------------------------------------------
# NODE 5 Display Enriched Results
#-----------------------------------------------------------------------------

def display_enriched_node(state:  AgentState) -> AgentState :
    people = state.get("enriched_people")
    companies = state.get("enriched_companies",[])

    if not people :
        print("\n No enriched profiles tio display")
        return {**state, "step": "no_enriched_date"}
    

    #company summary result
    _section(f" Enriched companioes - {len(companies)} profiles")

    for c in companies :
        print(f"\n  🏢 {c.get('name')}")
        _row("Funding",       f"{c.get('funding_stage')} | {c.get('funding_amount')}")
        _row("Team Size",     c.get("team_size", "Unknown"))
        _row("Tech Stack",    ", ".join(c.get("tech_stack", [])))
        _row("Growth Signal", c.get("growth_signal", "—"))
        if c.get("recent_news"):
            _row("Recent News",  c.get("recent_news", ["—"])[0])
        if c.get("pain_points"):
            _row("Pain Points",  " | ".join(c.get("pain_points", [])))

        
    #people profile 

    _section(f"Enriched people - {len(people)} contacts")


    by_company = {}
    for p in people:
        co = p.get("company", "Unknown")
        by_company.setdefault(co, []).append(p)

    for co, persons in by_company.items():
        persons.sort(key=lambda x: (
            0 if x.get("persona_type") == "primary" else 1,
            -x.get("confidence", 0)
        ))
        print(f"\n  🏢 {co}")

        for p in persons:
            tag  = "★ PRIMARY  " if p.get("persona_type") == "primary" else "· secondary"
            print(f"\n    [{tag}]  {p.get('name')}  —  {p.get('title', '—')}")

            if p.get("linkedin_url"):
                _row("LinkedIn",       p.get("linkedin_url"))
            if p.get("email_hint"):
                _row("Email",          p.get("email_hint"))
            if p.get("location"):
                _row("Location",       p.get("location"))
            if p.get("about"):
                _row("About",          p.get("about"))
            if p.get("expertise"):
                _row("Expertise",      ", ".join(p.get("expertise", [])))
            if p.get("recent_activity"):
                _row("Recent Activity",p.get("recent_activity", ["—"])[0])
            if p.get("best_hook"):
                _row("Best Hook",      p.get("best_hook"))
            _row("Confidence",         f"{p.get('confidence', '—')}/100")

    return {**state, "step": "enrichment_complete"}