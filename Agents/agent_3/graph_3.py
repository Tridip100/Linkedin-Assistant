from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_3 import (
    clean_profiles_node,
    enrich_people_node,
    enrich_companies_node,
    email_guess_node,
)

def build_enrichment_graph():
    builder = StateGraph(AgentState)

    # Nodes (ONLY existing ones)
    builder.add_node("clean_profiles", clean_profiles_node)
    builder.add_node("enrich_people", enrich_people_node)
    builder.add_node("enrich_companies", enrich_companies_node)
    builder.add_node("email_guess", email_guess_node)

    # Entry
    builder.set_entry_point("clean_profiles")

    # 1️⃣ Clean Profiles
    builder.add_conditional_edges(
        "clean_profiles",
        lambda s: s.get("step"),
        {
            "profiles_cleaned": "enrich_people",
            "clean_failed": END,
        },
    )

    # 2️⃣ Enrich People
    builder.add_conditional_edges(
        "enrich_people",
        lambda s: s.get("step"),
        {
            "people_enriched": "enrich_companies",
        },
    )

    # 3️⃣ Enrich Companies
    builder.add_conditional_edges(
        "enrich_companies",
        lambda s: s.get("step"),
        {
            "companies_enriched": "email_guess",
        },
    )

    # 4️⃣ Email Guess (FINAL STEP)
    builder.add_conditional_edges(
        "email_guess",
        lambda s: s.get("step"),
        {
            "emails_guessed": END,
        },
    )

    return builder.compile()