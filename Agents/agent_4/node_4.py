import re 
import json 
from core.state import AgentState
from core.llm import llm

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

def _ask_multi(question: str, options: list) -> list:
    print(f"\n  {question}")
    print("  (Enter numbers separated by commas e.g. 1,3)")
    for i, opt in enumerate(options, 1):
        print(f"    [{i}] {opt}")

    while True:
        try:
            raw     = input("\n  Your choices: ").strip()
            indices = [int(x.strip()) - 1 for x in raw.split(",")]
            if all(0 <= i < len(options) for i in indices):
                selected = [options[i] for i in indices]
                print(f"  ✓ Selected: {', '.join(selected)}")
                return selected
            else:
                print(f"  Please enter numbers between 1 and {len(options)}")
        except ValueError:
            print("  Please enter valid numbers separated by commas")


# ──────────────────────────────────────────────────────────────
# NODE 1 — AI Interview
# ──────────────────────────────────────────────────────────────

def priority_interview_node(state: AgentState) -> AgentState:
    enriched_people    = state.get("enriched_people", [])
    intent             = state.get("intent", {})
    companies          = state.get("enriched_companies", [])
    location           = intent.get("location", "any")  # ← fix: define location here

    if not enriched_people:
        return {**state,
                "error": "No enriched people to score.",
                "step":  "interview_failed"}

    _section("Priority Interview — Help me rank your leads")
    print(f"\n  I found {len(enriched_people)} enriched contacts.")
    print("  Let me ask you a few questions to rank them by YOUR priorities...\n")

    # ── Step 1: LLM generates relevant questions ──────────────
    question_prompt = f"""
You are a B2B lead scoring assistant.

The user searched for:
  Role/Domain      : {intent.get('role')}
  Opportunity Type : {intent.get('opportunity_type')}
  Location         : {intent.get('location')}
  Work Mode        : {intent.get('work_mode')}
  Experience Level : {intent.get('experience_level')}

Companies found    : {[c.get('name') for c in companies[:5]]}
People found       : {len(enriched_people)} contacts

Generate 5-6 smart, relevant interview questions to understand this user's
outreach priorities. Each question must have 3-4 specific options.

Questions must be RELEVANT to their search context:
  - If they searched "ML internship" → ask about fresher-friendly companies,
    mentorship, stipend range, tech stack relevance
  - If they searched "backend jobs" → ask about stack preference (Node/Python/Go),
    company size, remote vs onsite priority
  - If they searched "DevOps" → ask about cloud provider preference,
    startup vs enterprise, CI/CD stack importance
  - Always ask about: seniority of who to contact, location strictness,
    outreach channel preference

Return ONLY raw JSON. No markdown. Start with [ and end with ].

[
  {{
    "id": "q1",
    "question": "The actual question text",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "multi_select": true,
    "weight_key": "seniority"
  }}
]

Rules:
  - multi_select: true for all questions (user can always pick multiple)
  - weight_key must be one of: seniority, company_stage, location_match,
    has_email, has_linkedin, has_hook, tech_stack, confidence
  - Make questions conversational and specific to their domain
  - Never ask generic questions that don't relate to their search
"""

    try:
        raw       = llm.invoke(question_prompt).content.strip()
        questions = _parse_llm_json(raw)
        print(f"  Generated {len(questions)} personalized questions.\n")
    except Exception as e:
        print(f"  [Warning] Question generation failed: {e}")
        questions = [
            {
                "id": "q1",
                "question": "What seniority level do you want to prioritize?",
                "options": ["Founders and C-suite only", "VP and Director level", "Managers are fine", "Anyone works"],
                "multi_select": True,
                "weight_key": "seniority"
            },
            {
                "id": "q2",
                "question": "How important is location to you?",
                "options": ["Must be in my target city", "Same country preferred", "Location doesn't matter"],
                "multi_select": True,
                "weight_key": "location_match"
            },
            {
                "id": "q3",
                "question": "How do you plan to reach out?",
                "options": ["Email only", "LinkedIn DM", "Both preferred", "Either works"],
                "multi_select": True,
                "weight_key": "has_linkedin"
            },
            {
                "id": "q4",
                "question": "Does the company's tech stack matter?",
                "options": ["Yes — must match my domain", "Somewhat — modern stack preferred", "No — doesn't matter"],
                "multi_select": True,
                "weight_key": "tech_stack"
            },
            {
                "id": "q5",
                "question": "How important is having a personal talking point?",
                "options": ["Very — only contact people I have a hook for", "Preferred but not required", "Doesn't matter"],
                "multi_select": True,
                "weight_key": "has_hook"
            }
        ]

    # ── Step 2: Ask each generated question ───────────────────
    answers = {}

    for q in questions:
        qid        = q.get("id", "q")
        question   = q.get("question", "")
        options    = q.get("options", [])
        weight_key = q.get("weight_key", "")

        if not options:
            continue

        answer = _ask_multi(question, options)

        answers[qid] = {
            "question":   question,
            "answer":     answer,
            "weight_key": weight_key
        }

    print(f"\n  ✅ All answers recorded. Building your scoring config...")

    # ── Step 3: LLM converts answers into weight config ───────
    answers_text = "\n".join(
        f"  {v['question']} → {v['answer']}"
        for v in answers.values()
    )

    config_prompt = f"""
You are a B2B lead scoring strategist.

User's search context:
  Role             : {intent.get('role')}
  Opportunity Type : {intent.get('opportunity_type')}
  Location         : {location}
  Experience Level : {intent.get('experience_level')}

Their interview answers:
{answers_text}

Convert these answers into a precise scoring weight config.
Return ONLY raw JSON. No markdown. Start with {{ and end with }}.

{{
  "weights": {{
    "seniority":       0.0,
    "company_stage":   0.0,
    "location_match":  0.0,
    "has_email":       0.0,
    "has_linkedin":    0.0,
    "has_hook":        0.0,
    "tech_stack":      0.0,
    "confidence":      0.0
  }},
  "filters": {{
    "min_seniority":      [],
    "preferred_stages":   [],
    "require_email":      false,
    "require_linkedin":   true,
    "require_hook":       false,
    "preferred_location": "{location}"
  }},
  "goal": "one sentence describing the outreach goal"
}}

CRITICAL Rules:
  - All weights must add up to exactly 1.0
  - min_seniority MUST only use these exact values:
    "c_suite", "vp", "director", "manager", "individual_contributor"
  - min_seniority means MINIMUM level — always include all levels ABOVE it too:
    If human wants managers → ["c_suite", "vp", "director", "manager"]
    If human wants directors → ["c_suite", "vp", "director"]
    If human wants VP → ["c_suite", "vp"]
    If human wants founders/CEO/CTO only → ["c_suite"]
    If human said anyone works → [] (empty = no filter)
  - NEVER set min_seniority to just ["manager"] alone
    because that would filter out founders and CTOs which makes no sense
  - require_hook = true ONLY if human explicitly said hook is very important
  - preferred_location MUST be the actual city/country: {location}
  - If something doesn't matter → set weight to 0.05
"""

    try:
        raw    = llm.invoke(config_prompt).content.strip()
        config = _parse_llm_json(raw)

        _section("Scoring Configuration")
        print(f"\n  Goal: {config.get('goal')}")
        print("\n  Weights:")
        for k, v in config.get("weights", {}).items():
            bar = "█" * int(v * 20)
            print(f"    {k:<20} {bar:<20} {v}")
        print("\n  Filters:")
        for k, v in config.get("filters", {}).items():
            print(f"    {k:<25} {v}")

        return {**state,
                "scoring_config": config,
                "human_answers":  answers,
                "step":           "interview_done"}

    except Exception as e:
        print(f"\n  [Error] Config generation failed: {e}")
        default_config = {
            "weights": {
                "seniority":      0.25,
                "company_stage":  0.15,
                "location_match": 0.15,
                "has_email":      0.10,
                "has_linkedin":   0.10,
                "has_hook":       0.15,
                "tech_stack":     0.05,
                "confidence":     0.05
            },
            "filters": {
                "min_seniority":      ["c_suite", "vp"],
                "preferred_stages":   [],
                "require_email":      False,
                "require_linkedin":   True,
                "require_hook":       False,
                "preferred_location": location
            },
            "goal": "General B2B outreach"
        }
        return {**state,
                "scoring_config": default_config,
                "human_answers":  answers,
                "step":           "interview_done"}


# ──────────────────────────────────────────────────────────────
# NODE 2 — Scoring Engine
# ──────────────────────────────────────────────────────────────

def scoring_node(state: AgentState) -> AgentState:
    people    = state.get("enriched_people", [])
    companies = state.get("enriched_companies", [])
    config    = state.get("scoring_config", {})
    intent    = state.get("intent", {})

    weights = config.get("weights", {})
    filters = config.get("filters", {})

    company_map = {c.get("name", ""): c for c in companies}

    seniority_rank = {
        "c_suite":                100,
        "vp":                     85,
        "director":               70,
        "manager":                50,
        "individual_contributor": 30
    }

    funding_rank = {
        "Series C":     100,
        "Series B":     90,
        "Series A":     80,
        "Seed":         70,
        "Pre-seed":     60,
        "Bootstrapped": 40,
        "Public":       50,
        "Unknown":      20
    }

    preferred_stages   = filters.get("preferred_stages", [])
    preferred_location = filters.get("preferred_location", "any").lower()
    min_seniority      = filters.get("min_seniority", [])
    require_email      = filters.get("require_email", False)
    require_linkedin   = filters.get("require_linkedin", False)
    require_hook       = filters.get("require_hook", False)
    intent_location    = intent.get("location", "any").lower()

    _section("Scoring Leads")

    scored = []

    for p in people:
        name       = p.get("name", "")
        seniority  = p.get("seniority", "individual_contributor")
        company    = p.get("company", "")
        linkedin   = p.get("linkedin_url", "")
        email      = p.get("email_hint", "")
        hook       = p.get("best_hook", "")
        location   = p.get("location", "").lower()
        confidence = p.get("confidence", 0)

        co_data       = company_map.get(company, {})
        funding_stage = co_data.get("funding_stage", "Unknown")
        tech_stack    = [t.lower() for t in co_data.get("tech_stack", [])]
        pain_points   = co_data.get("pain_points", [])

        # ── Hard filters ───────────────────────────────────
        if require_email and not email:
            print(f"  ⚠ Filtered (no email): {name}")
            continue
        if require_linkedin and not linkedin:
            print(f"  ⚠ Filtered (no LinkedIn): {name}")
            continue
        if require_hook and not hook:
            print(f"  ⚠ Filtered (no hook): {name}")
            continue

        # ── Fix: only filter seniority if list is not empty ─
        # ── Safety: if min_seniority has manager but not c_suite, fix it ──
        if min_seniority and "manager" in min_seniority and "c_suite" not in min_seniority:
            min_seniority = ["c_suite", "vp", "director", "manager"]
            print(f"  [Auto-fix] min_seniority expanded to include all senior levels")
        # ── Dimension scores ───────────────────────────────
        seniority_score = seniority_rank.get(seniority, 30)

        stage_score = funding_rank.get(funding_stage, 20)
        if preferred_stages and funding_stage in preferred_stages:
            stage_score = min(stage_score + 20, 100)

        location_score = 0
        if preferred_location == "any" or intent_location == "any":
            location_score = 70
        elif preferred_location in location or intent_location in location:
            location_score = 100
        elif "india" in location:
            location_score = 60
        else:
            location_score = 30

        email_score    = 100 if email    else 0
        linkedin_score = 100 if linkedin else 0
        hook_score     = 100 if hook and len(hook) > 20 else 0

        ai_keywords = ["python", "pytorch", "tensorflow", "ml", "ai",
                       "nlp", "llm", "data science", "machine learning"]
        tech_score  = 0
        if tech_stack:
            matches    = sum(1 for k in ai_keywords if any(k in t for t in tech_stack))
            tech_score = min(matches * 20, 100)

        confidence_score = confidence

        final_score = (
            seniority_score  * weights.get("seniority",      0.25) +
            stage_score      * weights.get("company_stage",  0.20) +
            location_score   * weights.get("location_match", 0.10) +
            email_score      * weights.get("has_email",      0.15) +
            linkedin_score   * weights.get("has_linkedin",   0.10) +
            hook_score       * weights.get("has_hook",       0.10) +
            tech_score       * weights.get("tech_stack",     0.05) +
            confidence_score * weights.get("confidence",     0.05)
        )

        final_score = round(final_score, 1)

        scored.append({
            **p,
            "final_score": final_score,
            "score_breakdown": {
                "seniority":  round(seniority_score  * weights.get("seniority",      0.25), 1),
                "stage":      round(stage_score      * weights.get("company_stage",  0.20), 1),
                "location":   round(location_score   * weights.get("location_match", 0.10), 1),
                "email":      round(email_score      * weights.get("has_email",      0.15), 1),
                "linkedin":   round(linkedin_score   * weights.get("has_linkedin",   0.10), 1),
                "hook":       round(hook_score       * weights.get("has_hook",       0.10), 1),
                "tech":       round(tech_score       * weights.get("tech_stack",     0.05), 1),
                "confidence": round(confidence_score * weights.get("confidence",     0.05), 1),
            },
            "company_funding": funding_stage,
            "pain_points":     pain_points
        })

    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    print(f"\n  Scored {len(scored)} leads")
    return {**state, "scored_leads": scored, "step": "scoring_done"}


# ──────────────────────────────────────────────────────────────
# NODE 3 — Display Scored Leads
# ──────────────────────────────────────────────────────────────

def display_scores_node(state: AgentState) -> AgentState:
    scored = state.get("scored_leads", [])

    if not scored:
        print("\n  No leads were scored.")
        return {**state, "step": "no_scored_leads"}

    # ── Ask user how many to show ──────────────────────────
    print(f"\n  Total scored leads: {len(scored)}")
    raw = input(f"  How many leads to display? (press Enter for top 10, max {len(scored)}): ").strip()

    try:
        show = int(raw) if raw else 10
        show = min(show, len(scored))   # can't exceed total
    except ValueError:
        show = 10

    _section(f"Ranked Leads — Top {show} contacts")

    for i, p in enumerate(scored[:show], 1):
        score = p.get("final_score", 0)
        bar   = "█" * int(score // 10) + "░" * (10 - int(score // 10))

        print(f"\n  #{i}  {p.get('name')}  —  {p.get('title', '—')}")
        print(f"       {p.get('company')}  |  {p.get('company_funding', '—')}")
        print(f"       Score: {bar} {score}/100")

        breakdown = p.get("score_breakdown", {})
        print(f"       Breakdown: ", end="")
        print(" | ".join(f"{k}:{v}" for k, v in breakdown.items()))

        if p.get("linkedin_url"):
            _row("LinkedIn", p.get("linkedin_url"))
        if p.get("email_hint"):
            _row("Email",    p.get("email_hint"))
        if p.get("best_hook"):
            _row("Hook",     p.get("best_hook")[:70] + "...")

    print(f"\n  Showing {show}/{len(scored)} leads — rest passed to Agent 5 (Targeting)")
    return {**state, "step": "scores_displayed"}