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


def filter_targets_node(state: AgentState) -> AgentState:
    scored = state.get("scored_leads", [])
    logs   = []

    if not scored:
        return {**state, "error": "No scored leads to filter.", "step": "filter_failed", "logs": logs}

    skip_title_keywords = ["aspiring", "fresher", "student", "intern", "trainee", "learner",
                           "beginner", "junior", "entry level", "looking for", "seeking",
                           "graduate", "pursuing", "dreamer"]
    skip_name_keywords  = ["demo", "test", "bot", "official", "page", "account", "team",
                           "support", "admin", "path", "academy", "institute", "college", "university"]

    seen_urls  = set()
    by_company = {}

    for p in scored:
        name     = p.get("name", "").strip()
        title    = (p.get("title") or "").lower()
        linkedin = p.get("linkedin_url", "").strip()
        company  = p.get("company", "Unknown")
        score    = p.get("final_score", 0)

        if any(k in name.lower() for k in skip_name_keywords):
            _log(logs, "info", f"Removed non-person: {name}")
            continue
        if any(k in title for k in skip_title_keywords):
            _log(logs, "info", f"Removed student: {name}")
            continue
        if score < 50:
            _log(logs, "info", f"Removed low score {score}: {name}")
            continue
        if linkedin and linkedin in seen_urls:
            _log(logs, "info", f"Removed duplicate: {name}")
            continue
        if linkedin:
            seen_urls.add(linkedin)

        by_company.setdefault(company, []).append(p)

    filtered = []
    for company, persons in by_company.items():
        kept = persons[:4]
        filtered.extend(kept)
        for p in persons[4:]:
            _log(logs, "info", f"Removed limit 4/co: {p.get('name')} @ {company}")

    filtered.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    _log(logs, "success", f"Filtered: {len(scored)} → {len(filtered)}")

    if not filtered:
        return {**state, "error": "No valid targets after filtering.", "step": "filter_failed", "logs": logs}

    return {**state, "target_list": filtered, "step": "targets_filtered", "logs": logs}


def email_verify_node(state: AgentState) -> AgentState:
    targets = state.get("target_list", [])
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    logs    = []

    try:
        from core.config import ABSTRACT_API_KEY
        has_abstract = True
    except ImportError:
        has_abstract = False
        _log(logs, "info", "ABSTRACT_API_KEY not set — skipping verification")

    updated = []

    for p in targets:
        name     = p.get("name", "")
        company  = p.get("company", "")
        email    = p.get("email_hint", "")
        patterns = p.get("email_patterns", [])

        if email and "@" in email and has_abstract:
            try:
                resp        = requests.get("https://emailvalidation.abstractapi.com/v1/", params={"api_key": ABSTRACT_API_KEY, "email": email})
                result      = resp.json()
                deliverable = result.get("deliverability", "UNKNOWN")
                if deliverable == "DELIVERABLE":
                    p = {**p, "email_verified": True,  "email_status": "verified"}
                    _log(logs, "success", f"{name}: {email} ✅")
                elif deliverable == "UNDELIVERABLE":
                    p = {**p, "email_verified": False, "email_status": "invalid", "email_hint": ""}
                    _log(logs, "warning", f"{name}: {email} ❌")
                else:
                    p = {**p, "email_verified": False, "email_status": "unknown"}
                    _log(logs, "info", f"{name}: {email} ⚠")
            except Exception as e:
                _log(logs, "warning", f"Verify failed {name}: {e}")
                p = {**p, "email_verified": False, "email_status": "not_verified"}
        elif not email:
            query = f'"{name}" "{company}" email contact'
            try:
                resp        = requests.post("https://google.serper.dev/search", headers=headers, json={"q": query, "num": 3})
                results     = resp.json().get("organic", [])
                found_email = ""
                for r in results:
                    snippet = r.get("snippet", "") + r.get("title", "")
                    match   = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                    if match:
                        found_email = match.group(0)
                        break
                if found_email:
                    p = {**p, "email_hint": found_email, "email_status": "found"}
                    _log(logs, "success", f"{name}: {found_email} found")
                else:
                    best = patterns[0] if patterns else ""
                    p = {**p, "email_hint": best, "email_status": "pattern" if best else "none"}
                    _log(logs, "info", f"{name}: {best or 'no email'}")
            except Exception as e:
                _log(logs, "warning", f"Email search failed {name}: {e}")
                p = {**p, "email_status": "none"}
        else:
            p = {**p, "email_status": "unverified_pattern"}
            _log(logs, "info", f"{name}: {email} unverified")

        updated.append(p)

    return {**state, "target_list": updated, "step": "emails_verified", "logs": logs}


def shortlist_node(state: AgentState) -> AgentState:
    targets = state.get("target_list", [])
    intent  = state.get("intent", {})
    config  = state.get("scoring_config", {})
    logs    = []

    summary = "\n".join([
        f"{i+1}. {p.get('name')} | {p.get('title')} | {p.get('company')} | "
        f"Score:{p.get('final_score')} | Email:{p.get('email_hint','none')} | "
        f"LinkedIn:{(p.get('linkedin_url','none'))[:40]} | Hook:{(p.get('best_hook','none'))[:50]}"
        for i, p in enumerate(targets)
    ])

    prompt = f"""
B2B strategist. Goal:{config.get('goal')} | Role:{intent.get('role')} | Location:{intent.get('location')}
Return ONLY raw JSON array. Start with [ end with ].
[{{"name":"exact name","priority":"HIGH|MEDIUM|LOW","channel":"email|linkedin|both","strategy":"one sentence"}}]
HIGH=score>=65 AND (email OR hook) AND decision maker. MEDIUM=55-64. LOW=<55.
channel: email=has email no linkedin. linkedin=has linkedin no email. both=has both.
Leads: {summary}
"""
    try:
        raw          = llm.invoke(prompt).content.strip()
        priorities   = _parse_llm_json(raw)
        priority_map = {p.get("name"): p for p in priorities}

        updated = []
        for p in targets:
            pr = priority_map.get(p.get("name", ""), {})
            updated.append({**p,
                "priority": pr.get("priority", "MEDIUM"),
                "channel":  pr.get("channel",  "linkedin"),
                "strategy": pr.get("strategy", "")})

        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        updated.sort(key=lambda x: (priority_order.get(x.get("priority", "LOW"), 2), -x.get("final_score", 0)))

        high   = sum(1 for p in updated if p.get("priority") == "HIGH")
        medium = sum(1 for p in updated if p.get("priority") == "MEDIUM")
        low    = sum(1 for p in updated if p.get("priority") == "LOW")
        _log(logs, "success", f"Shortlist: HIGH={high} MEDIUM={medium} LOW={low}")

        return {**state, "target_list": updated, "step": "shortlist_done", "logs": logs}

    except Exception as e:
        _log(logs, "warning", f"Shortlist failed: {e}")
        return {**state, "step": "shortlist_done", "logs": logs}


def build_dashboard_node(state: AgentState) -> AgentState:
    logs      = []
    companies = state.get("companies", [])
    people    = state.get("discovered_people", [])
    enriched  = state.get("enriched_people", [])
    scored    = state.get("scored_leads", [])
    targets   = state.get("target_list", [])

    high   = sum(1 for p in targets if p.get("priority") == "HIGH")
    medium = sum(1 for p in targets if p.get("priority") == "MEDIUM")
    low    = sum(1 for p in targets if p.get("priority") == "LOW")
    emails = sum(1 for p in targets if p.get("email_hint"))
    li     = sum(1 for p in targets if p.get("linkedin_url"))

    dashboard = {
        "companies_found":    len(companies),
        "people_found":       len(people),
        "after_enrichment":   len(enriched),
        "after_scoring":      len(scored),
        "final_targets":      len(targets),
        "high_priority":      high,
        "medium_priority":    medium,
        "low_priority":       low,
        "emails_found":       emails,
        "linkedin_found":     li,
        "messages_generated": len(state.get("generated_messages", [])),
    }

    _log(logs, "success", "Dashboard ready")
    return {**state, "dashboard_stats": dashboard, "step": "dashboard_ready", "logs": logs}