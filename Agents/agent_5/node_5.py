import re
import json
import csv
import os
import requests
from core.state import AgentState
from core.llm import llm
from core.config import SERPER_API_KEY


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
    print(f"  {label:<25} {value}")

def _ask(question: str, options: list) -> str:
    print(f"\n  {question}")
    for i, opt in enumerate(options, 1):
        print(f"    [{i}] {opt}")
    while True:
        try:
            raw    = input("\n  Your choice: ").strip()
            choice = int(raw) - 1
            if 0 <= choice < len(options):
                selected = options[choice]
                print(f"  ✓ Selected: {selected}")
                return selected
            else:
                print(f"  Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("  Please enter a valid number")


# ──────────────────────────────────────────────────────────────
# NODE 1 — Filter & Deduplicate
# ──────────────────────────────────────────────────────────────

def filter_targets_node(state: AgentState) -> AgentState:
    """
    - Remove duplicates by LinkedIn URL
    - Remove students/aspirants/freshers
    - Remove non-persons
    - Keep max 4 per company (best scored)
    - Apply minimum score threshold
    """
    scored = state.get("scored_leads", [])

    if not scored:
        return {**state,
                "error": "No scored leads to filter.",
                "step":  "filter_failed"}

    _section("Filtering & Deduplicating Leads")

    # Keywords that indicate non-target profiles
    skip_title_keywords = [
        "aspiring", "fresher", "student", "intern",
        "trainee", "learner", "beginner", "junior",
        "entry level", "looking for", "seeking",
        "graduate", "pursuing", "dreamer"
    ]

    skip_name_keywords = [
        "demo", "test", "bot", "official", "page",
        "account", "team", "support", "admin", "path",
        "academy", "institute", "college", "university"
    ]

    seen_urls    = set()
    by_company   = {}
    removed_log  = []

    for p in scored:
        name     = p.get("name", "").strip()
        title    = (p.get("title") or "").lower()
        linkedin = p.get("linkedin_url", "").strip()
        company  = p.get("company", "Unknown")
        score    = p.get("final_score", 0)

        # ── Remove non-persons ─────────────────────────────
        if any(k in name.lower() for k in skip_name_keywords):
            removed_log.append(f"  ✗ Non-person   : {name}")
            continue

        # ── Remove students/aspirants ──────────────────────
        if any(k in title for k in skip_title_keywords):
            removed_log.append(f"  ✗ Student/Aspir: {name} ({p.get('title')})")
            continue

        # ── Remove below score threshold ───────────────────
        if score < 50:
            removed_log.append(f"  ✗ Low score    : {name} ({score})")
            continue

        # ── Deduplicate by LinkedIn URL ────────────────────
        if linkedin and linkedin in seen_urls:
            removed_log.append(f"  ✗ Duplicate    : {name}")
            continue
        if linkedin:
            seen_urls.add(linkedin)

        # ── Group by company ───────────────────────────────
        by_company.setdefault(company, []).append(p)

    # ── Keep max 4 per company (already sorted by score) ──
    filtered = []
    for company, persons in by_company.items():
        kept = persons[:4]   # top 4 per company
        filtered.extend(kept)
        if len(persons) > 4:
            for p in persons[4:]:
                removed_log.append(f"  ✗ Limit (>{4}/co): {p.get('name')} @ {company}")

    # Sort final list by score
    filtered.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    # Print removal log
    if removed_log:
        print("\n  Removed:")
        for log in removed_log:
            print(f"  {log}")

    print(f"\n  Input  : {len(scored)} scored leads")
    print(f"  Output : {len(filtered)} clean targets")
    print(f"  Removed: {len(scored) - len(filtered)} leads")

    if not filtered:
        return {**state,
                "error": "No valid targets after filtering.",
                "step":  "filter_failed"}

    return {**state, "target_list": filtered, "step": "targets_filtered"}


# ──────────────────────────────────────────────────────────────
# NODE 2 — Email Verification (Abstract API)
# ──────────────────────────────────────────────────────────────

def email_verify_node(state: AgentState) -> AgentState:
    """
    - Verify existing emails via Abstract API
    - Try to find emails for people missing one via Serper
    """
    targets  = state.get("target_list", [])
    headers  = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    # Get Abstract API key from config
    try:
        from core.config import ABSTRACT_API_KEY
        has_abstract = True
    except ImportError:
        has_abstract = False
        print("  [Info] ABSTRACT_API_KEY not set — skipping email verification")

    _section("Email Verification")

    updated = []

    for p in targets:
        name     = p.get("name", "")
        company  = p.get("company", "")
        email    = p.get("email_hint", "")
        patterns = p.get("email_patterns", [])

        # ── Verify existing email ──────────────────────────
        if email and "@" in email and has_abstract:
            try:
                resp = requests.get(
                    "https://emailvalidation.abstractapi.com/v1/",
                    params={
                        "api_key": ABSTRACT_API_KEY,
                        "email":   email
                    }
                )
                result       = resp.json()
                deliverable  = result.get("deliverability", "UNKNOWN")
                is_valid     = result.get("is_valid_format", {}).get("value", False)

                if deliverable == "DELIVERABLE":
                    p = {**p, "email_verified": True,  "email_status": "✅ Verified"}
                    print(f"  {name:<30} → {email} ✅ DELIVERABLE")
                elif deliverable == "UNDELIVERABLE":
                    p = {**p, "email_verified": False, "email_status": "❌ Invalid",
                         "email_hint": ""}
                    print(f"  {name:<30} → {email} ❌ UNDELIVERABLE")
                else:
                    p = {**p, "email_verified": False, "email_status": "⚠ Unknown"}
                    print(f"  {name:<30} → {email} ⚠ UNKNOWN")

            except Exception as e:
                print(f"  [Warning] Verification failed for {name}: {e}")
                p = {**p, "email_verified": False, "email_status": "⚠ Not verified"}

        # ── Try to find email if missing ───────────────────
        elif not email:
            query = f'"{name}" "{company}" email contact'
            try:
                resp    = requests.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query, "num": 3}
                )
                results = resp.json().get("organic", [])

                found_email = ""
                for r in results:
                    snippet = r.get("snippet", "") + r.get("title", "")
                    # Look for email pattern in snippet
                    email_match = re.search(
                        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                        snippet
                    )
                    if email_match:
                        found_email = email_match.group(0)
                        break

                if found_email:
                    p = {**p, "email_hint": found_email, "email_status": "📧 Found"}
                    print(f"  {name:<30} → {found_email} 📧 Found via search")
                else:
                    # Use first pattern as best guess
                    best_guess = patterns[0] if patterns else ""
                    p = {**p,
                         "email_hint":   best_guess,
                         "email_status": "💡 Pattern guess" if best_guess else "❌ No email"}
                    print(f"  {name:<30} → {best_guess or 'no email found'}")

            except Exception as e:
                print(f"  [Warning] Email search failed for {name}: {e}")
                p = {**p, "email_status": "❌ No email"}
        else:
            p = {**p, "email_status": "💡 Unverified pattern"}
            print(f"  {name:<30} → {email} (unverified pattern)")

        updated.append(p)

    return {**state, "target_list": updated, "step": "emails_verified"}


# ──────────────────────────────────────────────────────────────
# NODE 3 — Final Shortlist + Priority Assignment
# ──────────────────────────────────────────────────────────────

def shortlist_node(state: AgentState) -> AgentState:
    """
    LLM reviews final list and assigns:
    - Outreach priority: HIGH / MEDIUM / LOW
    - Best contact channel: email / linkedin / both
    - One line outreach strategy per person
    """
    targets = state.get("target_list", [])
    intent  = state.get("intent", {})
    config  = state.get("scoring_config", {})

    _section("Building Final Shortlist")

    # Build summary for LLM
    people_summary = "\n".join([
        f"{i+1}. {p.get('name')} | {p.get('title')} | {p.get('company')} | "
        f"Score:{p.get('final_score')} | "
        f"Email:{p.get('email_hint', 'none')} | "
        f"LinkedIn:{p.get('linkedin_url', 'none')[:40]} | "
        f"Hook:{p.get('best_hook', 'none')[:50]}"
        for i, p in enumerate(targets)
    ])

    prompt = f"""
You are a B2B outreach strategist.

User's goal    : {config.get('goal', 'B2B outreach')}
Role searching : {intent.get('role')}
Location       : {intent.get('location')}

Review these leads and assign priority + channel for each.
Return ONLY raw JSON array. No markdown. Start with [ end with ].

[
  {{
    "name": "exact name from list",
    "priority": "HIGH | MEDIUM | LOW",
    "channel": "email | linkedin | both",
    "strategy": "One specific sentence on how to approach this person"
  }}
]

Priority rules:
  HIGH   = score >= 65 AND (has email OR strong hook) AND decision maker
  MEDIUM = score 55-64 OR missing one key element
  LOW    = score < 55 OR student/junior (keep for future)

Channel rules:
  email   = has verified/pattern email, no LinkedIn
  linkedin = has LinkedIn URL, no email
  both    = has both

Leads to review:
{people_summary}
"""

    try:
        raw        = llm.invoke(prompt).content.strip()
        priorities = _parse_llm_json(raw)

        # Merge priorities back into target list
        priority_map = {p.get("name"): p for p in priorities}

        updated = []
        for p in targets:
            name     = p.get("name", "")
            priority = priority_map.get(name, {})
            updated.append({
                **p,
                "priority": priority.get("priority", "MEDIUM"),
                "channel":  priority.get("channel",  "linkedin"),
                "strategy": priority.get("strategy", "")
            })

        # Sort by priority then score
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        updated.sort(key=lambda x: (
            priority_order.get(x.get("priority", "LOW"), 2),
            -x.get("final_score", 0)
        ))

        high   = sum(1 for p in updated if p.get("priority") == "HIGH")
        medium = sum(1 for p in updated if p.get("priority") == "MEDIUM")
        low    = sum(1 for p in updated if p.get("priority") == "LOW")

        print(f"\n  HIGH   : {high} contacts")
        print(f"  MEDIUM : {medium} contacts")
        print(f"  LOW    : {low} contacts")

        return {**state, "target_list": updated, "step": "shortlist_done"}

    except Exception as e:
        print(f"\n  [Error] Shortlist generation failed: {e}")
        return {**state, "step": "shortlist_done"}   # continue anyway


# ──────────────────────────────────────────────────────────────
# NODE 4 — Display Final Targets
# ──────────────────────────────────────────────────────────────

def display_targets_node(state: AgentState) -> AgentState:
    targets = state.get("target_list", [])

    if not targets:
        print("\n  No targets to display.")
        return {**state, "step": "no_targets"}

    _section(f"Final Target List — {len(targets)} contacts")

    priority_colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

    for i, p in enumerate(targets, 1):
        priority = p.get("priority", "MEDIUM")
        icon     = priority_colors.get(priority, "🟡")
        score    = p.get("final_score", 0)
        bar      = "█" * int(score // 10) + "░" * (10 - int(score // 10))

        print(f"\n  {icon} #{i}  [{priority}]  {p.get('name')}  —  {p.get('title', '—')}")
        print(f"       {p.get('company')}  |  Score: {bar} {score}/100")

        if p.get("linkedin_url"):
            _row("LinkedIn",  p.get("linkedin_url"))
        if p.get("email_hint"):
            _row("Email",     f"{p.get('email_hint')}  {p.get('email_status', '')}")
        if p.get("location"):
            _row("Location",  p.get("location"))
        if p.get("channel"):
            _row("Channel",   p.get("channel").upper())
        if p.get("strategy"):
            _row("Strategy",  p.get("strategy"))
        if p.get("best_hook"):
            _row("Hook",      p.get("best_hook")[:70] + "...")

    # ── Human decision on CSV export ──────────────────────
    export = _ask(
        "Do you want to export this target list to CSV?",
        [
            "Yes — export all targets",
            "Yes — export HIGH priority only",
            "No — skip export"
        ]
    )

    if "No" not in export:
        export_targets = targets
        if "HIGH" in export:
            export_targets = [p for p in targets if p.get("priority") == "HIGH"]

        # Write CSV
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "output_leads.csv"
        )
        output_path = os.path.normpath(output_path)

        fields = [
            "name", "title", "company", "final_score", "priority",
            "channel", "linkedin_url", "email_hint", "email_status",
            "location", "best_hook", "strategy", "company_funding"
        ]

        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(export_targets)

            print(f"\n  ✅ Exported {len(export_targets)} contacts to:")
            print(f"     {output_path}")

        except Exception as e:
            print(f"\n  [Error] CSV export failed: {e}")
    else:
        print("\n  Skipped CSV export.")

    return {**state, "step": "targets_displayed"}