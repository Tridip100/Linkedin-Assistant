import re
import json
import requests
from urllib.parse import urlparse
from core.llm import llm
from core.config import SERPER_API_KEY, APPOLO_API_KEY
from core.state import AgentState


def _parse_llm_json(raw: str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)

def _log(logs: list, level: str, msg: str):
    logs.append({"level": level, "msg": msg})

def _is_valid_profile_url(url: str) -> bool:
    if not url:
        return False
    return "/in/" in url and "/posts/" not in url and "crunchbase" not in url


def clean_profiles_node(state: AgentState) -> AgentState:
    people = state.get("discovered_people", [])
    logs   = []

    if not people:
        return {**state, "error": "No people to enrich.", "step": "clean_failed", "logs": logs}

    cleaned       = []
    seen_urls     = set()
    skip_keywords = ["demo", "test", "bot", "official", "page", "account", "team", "support", "admin", "info"]

    for p in people:
        name     = p.get("name", "").strip()
        title    = p.get("title", "").strip()
        linkedin = p.get("linkedin_url", "").strip()
        company  = p.get("company", "")

        if not name or name.lower() in ["unknown", "none", ""]:
            _log(logs, "info", f"Skipped no name [{company}]")
            continue
        if any(k in name.lower() for k in skip_keywords):
            _log(logs, "info", f"Skipped non-person: {name}")
            continue
        if linkedin and not _is_valid_profile_url(linkedin):
            match    = re.search(r"/posts/([a-zA-Z0-9\-]+)_", linkedin)
            linkedin = f"https://www.linkedin.com/in/{match.group(1)}" if match else ""
        if linkedin and linkedin in seen_urls:
            _log(logs, "info", f"Duplicate: {name}")
            continue
        if linkedin:
            seen_urls.add(linkedin)

        cleaned.append({**p, "name": name, "title": title, "linkedin_url": linkedin,
                        "email": "", "recent_posts": [], "enriched": False})

    _log(logs, "success", f"Cleaned: {len(people)} → {len(cleaned)}")
    return {**state, "discovered_people": cleaned, "step": "profiles_cleaned", "logs": logs}


def enrich_people_node(state: AgentState) -> AgentState:
    people  = state.get("discovered_people", [])
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    logs    = []

    enriched_people = []

    for p in people:
        name    = p.get("name", "")
        company = p.get("company", "")
        title   = p.get("title", "")

        queries      = [f'"{name}" "{company}" linkedin', f'"{name}" {company} interview OR podcast OR article']
        all_snippets = []

        for query in queries:
            try:
                resp    = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query.strip(), "num": 5})
                results = resp.json().get("organic", [])
                all_snippets.extend([{"title": r.get("title",""), "snippet": r.get("snippet",""), "link": r.get("link","")} for r in results])
            except Exception as e:
                _log(logs, "warning", f"Search failed for {name}: {e}")

        if not all_snippets:
            enriched_people.append(p)
            _log(logs, "info", f"{name}: no data")
            continue

        snippets_text = "\n".join(f"Title:{s['title']} | Snippet:{s['snippet']} | Link:{s['link']}" for s in all_snippets[:10])

        prompt = f"""
Enrich B2B contact. Person:{name}, Company:{company}, Title:{title}
Return ONLY raw JSON. Start with {{ end with }}.
{{
  "confirmed_title": "current title",
  "confirmed_company": "company name",
  "linkedin_url": "LinkedIn /in/ URL or empty",
  "email_hint": "email if found or empty",
  "location": "City, Country or empty",
  "about": "1-2 sentence summary",
  "recent_activity": ["recent topics max 3"],
  "expertise": ["key skills max 4"],
  "best_hook": "specific thing to reference when reaching out"
}}
Rules: extract only from data, current role only, reject /posts/ URLs.
Data: {snippets_text}
"""
        try:
            raw      = llm.invoke(prompt).content.strip()
            enriched = _parse_llm_json(raw)
            updated  = {
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
            _log(logs, "success", f"{name}: enriched ✓")
        except Exception as e:
            enriched_people.append(p)
            _log(logs, "warning", f"Enrichment failed for {name}: {e}")

    return {**state, "enriched_people": enriched_people, "step": "people_enriched", "logs": logs}


def enrich_companies_node(state: AgentState) -> AgentState:
    companies = state.get("companies", [])
    headers   = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    logs      = []

    enriched_companies = []

    for company in companies:
        name   = company.get("name", "")
        domain = company.get("website_domain", "")

        apollo_data = {}

        if domain:
            try:
                resp = requests.get(
                    "https://api.apollo.io/v1/organizations/enrich",
                    params={"api_key": APPOLO_API_KEY, "domain": domain}
                )
                org = resp.json().get("organization", {})
                if org:
                    raw_stack  = org.get("technologies", [])
                    tech_stack = [t.get("name", t) if isinstance(t, dict) else t for t in raw_stack]
                    apollo_data = {
                        "funding_stage":    org.get("latest_funding_stage") or "Unknown",
                        "funding_amount":   str(org.get("total_funding") or "Unknown"),
                        "team_size":        str(org.get("estimated_num_employees") or "Unknown"),
                        "tech_stack":       tech_stack,
                        "company_linkedin": org.get("linkedin_url", ""),
                        "website":          org.get("website_url", ""),
                        "growth_signal":    org.get("short_description", ""),
                        "industry":         org.get("industry", "")
                    }
                    _log(logs, "success", f"{name}: Apollo ✓")
            except Exception as e:
                _log(logs, "warning", f"Apollo failed for {name}: {e}")

        queries      = [
            f'"{name}" funding OR raised site:crunchbase.com OR site:techcrunch.com',
            f'"{name}" news OR launch 2024 OR 2025',
        ]
        all_snippets = []

        for query in queries:
            try:
                resp    = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query.strip(), "num": 5})
                results = resp.json().get("organic", [])
                all_snippets.extend([{"title": r.get("title",""), "snippet": r.get("snippet","")} for r in results])
            except Exception as e:
                _log(logs, "warning", f"Serper failed for {name}: {e}")

        serper_enriched = {}
        if all_snippets:
            snippets_text = "\n".join(f"Title:{s['title']} | Snippet:{s['snippet']}" for s in all_snippets[:10])
            prompt = f"""
Enrich company {name}. Funding:{apollo_data.get('funding_stage','Unknown')}, Team:{apollo_data.get('team_size','Unknown')}
Return ONLY raw JSON. Start with {{ end with }}.
{{
  "recent_news": ["1-2 recent events"],
  "pain_points": ["1-2 challenges"],
  "funding_stage": "only if unknown else empty",
  "funding_amount": "only if unknown else empty"
}}
Data: {snippets_text}
"""
            try:
                raw             = llm.invoke(prompt).content.strip()
                serper_enriched = _parse_llm_json(raw)
            except Exception as e:
                _log(logs, "warning", f"LLM enrichment failed for {name}: {e}")

        if not apollo_data and not serper_enriched:
            enriched_companies.append(company)
            _log(logs, "info", f"{name}: no data")
            continue

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
        enriched_companies.append(updated)
        _log(logs, "success", f"{name}: {updated.get('funding_stage')} | {updated.get('team_size')}")

    _log(logs, "success", f"Companies enriched: {len(enriched_companies)}")
    return {**state, "enriched_companies": enriched_companies, "step": "companies_enriched", "logs": logs}


def email_guess_node(state: AgentState) -> AgentState:
    people             = state.get("enriched_people", [])
    enriched_companies = state.get("enriched_companies", [])
    logs               = []

    domain_map = {}
    for c in enriched_companies:
        name    = c.get("name", "")
        website = c.get("website", "")
        if website:
            parsed = urlparse(website)
            domain = parsed.netloc.replace("www.", "")
            if domain:
                domain_map[name] = domain

    updated_people = []

    for p in people:
        name       = p.get("name", "")
        company    = p.get("company", "")
        email_hint = p.get("email_hint", "")

        if email_hint and "@" in email_hint:
            updated_people.append(p)
            _log(logs, "success", f"{name}: {email_hint}")
            continue

        domain = domain_map.get(company, "")
        if not domain or not name:
            updated_people.append(p)
            _log(logs, "info", f"{name}: no domain")
            continue

        parts    = name.lower().split()
        first    = parts[0] if parts else ""
        last     = parts[-1] if len(parts) > 1 else ""
        patterns = []

        if first and last:
            patterns = [f"{first}@{domain}", f"{first}.{last}@{domain}", f"{first[0]}{last}@{domain}", f"{first}_{last}@{domain}"]
        elif first:
            patterns = [f"{first}@{domain}"]

        updated_people.append({**p, "email_patterns": patterns, "email_hint": patterns[0] if patterns else ""})
        _log(logs, "info", f"{name}: {patterns[0] if patterns else 'no pattern'}")

    return {**state, "enriched_people": updated_people, "step": "emails_guessed", "logs": logs}