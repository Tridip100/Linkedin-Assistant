import re
import json
from core.state import AgentState
from core.llm import llm


def _parse_llm_json(raw: str):
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    return json.loads(cleaned)

def _log(logs: list, level: str, msg: str):
    logs.append({"level": level, "msg": msg})


def build_sender_bio_node(state: AgentState) -> AgentState:
    profile = state.get("sender_profile", {})
    logs    = []

    if not profile or not profile.get("name"):
        return {**state, "error": "No sender profile provided.", "step": "profile_failed", "logs": logs}

    skills = profile.get("skills", [])
    prompt = f"""
Write a compelling 2-line professional bio for outreach messages.
Name:{profile.get('name')}, College:{profile.get('college')}, Degree:{profile.get('degree')},
Year:{profile.get('year')}, Skills:{', '.join(skills)}, Project:{profile.get('project')},
Achievement:{profile.get('achieve')}, Goal:{profile.get('goal')}
Rules: Max 2 sentences under 50 words. Human confident. Most impressive first. No "passionate"/"enthusiastic".
Return ONLY the bio text. No quotes.
"""
    try:
        bio = llm.invoke(prompt).content.strip()
    except Exception:
        bio = f"{profile.get('degree')} from {profile.get('college')} with {', '.join(skills[:3])}. Looking for {profile.get('goal')}."

    _log(logs, "success", f"Bio generated for {profile.get('name')}")
    return {**state, "sender_profile": {**profile, "bio": bio}, "step": "profile_collected", "logs": logs}


def generate_messages_node(state: AgentState) -> AgentState:
    targets = state.get("target_list", [])
    profile = state.get("sender_profile", {})
    intent  = state.get("intent", {})
    config  = state.get("scoring_config", {})
    logs    = []

    all_messages = []

    for p in targets:
        name        = p.get("name", "")
        title       = p.get("title", "")
        company     = p.get("company", "")
        hook        = p.get("best_hook", "")
        about       = p.get("about", "")
        expertise   = p.get("expertise", [])
        recent      = p.get("recent_activity", [])
        pain_points = p.get("pain_points", [])
        funding     = p.get("company_funding", "")
        priority    = p.get("priority", "MEDIUM")
        channel     = p.get("channel", "linkedin")
        strategy    = p.get("strategy", "")

        prompt = f"""
Expert B2B outreach copywriter.
SENDER: Name:{profile.get('name')}, Background:{profile.get('degree')} from {profile.get('college')},
Skills:{', '.join(profile.get('skills',[]))}, Project:{profile.get('project')},
Achievement:{profile.get('achieve')}, LinkedIn:{profile.get('linkedin')}, Goal:{profile.get('goal')}, Bio:{profile.get('bio')}

RECIPIENT: Name:{name}, Title:{title}, Company:{company}, About:{about},
Expertise:{', '.join(expertise)}, Hook:{hook}, Recent:{', '.join(recent[:2]) if recent else 'none'},
Pain points:{', '.join(pain_points[:2]) if pain_points else 'none'}, Funding:{funding}, Strategy:{strategy}

GOAL: {config.get('goal', intent.get('opportunity_type', 'opportunity'))}

Generate 4 messages. Return ONLY raw JSON. Start with {{ end with }}.
{{
  "linkedin_request": {{"message": "MAX 300 chars. Reference hook. Brief intro. Soft connect reason. No I saw your profile.", "char_count": 0}},
  "linkedin_dm":      {{"message": "100-150 words. Reference hook. Relevant skill. Soft question CTA.", "word_count": 0}},
  "cold_email":       {{"subject": "Under 8 words. Specific. No Following up.", "body": "120-150 words. Hook→background→CTA. Sign name+LinkedIn.", "word_count": 0}},
  "followup":         {{"message": "50-70 words. Different angle. Not desperate.", "word_count": 0}}
}}
NEVER: passionate, enthusiastic, reach out, touch base, I hope this finds you well, I came across your profile.
Hook: {hook[:100] if hook else 'their work at ' + company}
"""
        try:
            raw      = llm.invoke(prompt).content.strip()
            messages = _parse_llm_json(raw)

            messages["person"]       = name
            messages["company"]      = company
            messages["title"]        = title
            messages["priority"]     = priority
            messages["channel"]      = channel
            messages["linkedin_url"] = p.get("linkedin_url", "")
            messages["email"]        = p.get("email_hint", "")

            lr = messages.get("linkedin_request", {})
            lr["char_count"] = len(lr.get("message", ""))
            dm = messages.get("linkedin_dm", {})
            dm["word_count"] = len(dm.get("message", "").split())
            ce = messages.get("cold_email", {})
            ce["word_count"] = len(ce.get("body", "").split())
            fu = messages.get("followup", {})
            fu["word_count"] = len(fu.get("message", "").split())

            all_messages.append(messages)
            _log(logs, "success", f"{name}: messages ✓")
        except Exception as e:
            _log(logs, "error", f"Message failed for {name}: {e}")

    _log(logs, "success", f"Generated {len(all_messages)}/{len(targets)}")
    return {**state, "generated_messages": all_messages, "step": "messages_generated", "logs": logs}


def quality_score_node(state: AgentState) -> AgentState:
    messages = state.get("generated_messages", [])
    profile  = state.get("sender_profile", {})
    logs     = []

    reviewed = []

    for m in messages:
        name    = m.get("person", "")
        hook    = m.get("linkedin_request", {}).get("message", "")
        dm      = m.get("linkedin_dm", {}).get("message", "")
        subject = m.get("cold_email", {}).get("subject", "")
        body    = m.get("cold_email", {}).get("body", "")

        prompt = f"""
Review B2B outreach for {name}.
Return ONLY raw JSON. Start with {{ end with }}.
{{
  "personalization": 0, "clarity": 0, "cta_strength": 0,
  "spam_risk": 0, "overall": 0, "rewrite_needed": false,
  "issues": ["problems"]
}}
personalization=specific refs, clarity=clear ask, cta_strength=soft compelling,
spam_risk=10 very spammy 1 natural (lower better), overall=avg(p+c+cta)-spam/2.
rewrite_needed=true if overall<7 OR spam_risk>6.
LI Request:{hook[:200]} DM:{dm[:300]} Subject:{subject} Body:{body[:400]}
"""
        try:
            raw     = llm.invoke(prompt).content.strip()
            scores  = _parse_llm_json(raw)
            overall = scores.get("overall", 7)
            rewrite = scores.get("rewrite_needed", False)
            issues  = scores.get("issues", [])

            _log(logs, "info", f"{name}: quality {overall}/10 spam {scores.get('spam_risk')}/10")

            if rewrite:
                rewrite_prompt = f"""
Rewrite outreach for {name}. Fix: {', '.join(issues)}
Original LI:{hook} DM:{dm} Subject:{subject} Body:{body}
Sender:{profile.get('bio')}, Skills:{', '.join(profile.get('skills', []))}
Return ONLY raw JSON same structure. Start with {{ end with }}.
{{"linkedin_request":{{"message":""}},"linkedin_dm":{{"message":""}},"cold_email":{{"subject":"","body":""}},"followup":{{"message":""}}}}
"""
                try:
                    raw2      = llm.invoke(rewrite_prompt).content.strip()
                    rewritten = _parse_llm_json(raw2)
                    m = {**m,
                         "linkedin_request": rewritten.get("linkedin_request", m["linkedin_request"]),
                         "linkedin_dm":      rewritten.get("linkedin_dm",      m["linkedin_dm"]),
                         "cold_email":       rewritten.get("cold_email",       m["cold_email"]),
                         "followup":         rewritten.get("followup",         m["followup"]),
                         "rewritten":        True}
                    _log(logs, "success", f"{name}: rewritten ✓")
                except Exception as e:
                    _log(logs, "warning", f"Rewrite failed {name}: {e}")

            m["quality_scores"] = scores
            reviewed.append(m)
        except Exception as e:
            _log(logs, "warning", f"Quality check failed {name}: {e}")
            reviewed.append(m)

    return {**state, "generated_messages": reviewed, "step": "quality_checked", "logs": logs}


def campaign_planner_node(state: AgentState) -> AgentState:
    messages = state.get("generated_messages", [])
    logs     = []

    high   = [m for m in messages if m.get("priority") == "HIGH"]
    medium = [m for m in messages if m.get("priority") == "MEDIUM"]
    low    = [m for m in messages if m.get("priority") == "LOW"]

    plan = {
        "day_1": {"action": "Send LinkedIn requests to HIGH priority", "contacts": [m.get("person") for m in high], "note": "Max 5-10/day"},
        "day_2": {"action": "Send cold emails to HIGH priority",       "contacts": [m.get("person") for m in high if m.get("email")], "note": "Email only"},
        "day_3": {"action": "Send LinkedIn requests to MEDIUM",        "contacts": [m.get("person") for m in medium], "note": "Expand outreach"},
        "day_4": {"action": "Send DMs to accepted connections",        "contacts": [m.get("person") for m in high], "note": "Check acceptances"},
        "day_5": {"action": "Follow up no-reply HIGH contacts",        "contacts": [m.get("person") for m in high], "note": "Different angle"},
        "day_6": {"action": "Send emails to MEDIUM priority",          "contacts": [m.get("person") for m in medium if m.get("email")], "note": "Expand emails"},
        "day_7": {"action": "Review responses + plan next week",       "contacts": [], "note": "Move responders to CRM"},
    }

    _log(logs, "success", f"Campaign: {len(high)} HIGH {len(medium)} MEDIUM {len(low)} LOW")
    return {**state, "campaign_plan": plan, "step": "campaign_planned", "logs": logs}