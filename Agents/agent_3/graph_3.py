from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_3 import(
    clean_profiles_node,
    enrich_people_node,
    enrich_companies_node,
    email_guess_node,
    display_enriched_node,
)

def build_enrichment_graph() :
    builder = StateGraph(AgentState)

    builder.add_node("clean_profiles",    clean_profiles_node)
    builder.add_node("enrich_people",     enrich_people_node)
    builder.add_node("enrich_companies",  enrich_companies_node)
    builder.add_node("email_guess",       email_guess_node)
    builder.add_node("display_enriched",  display_enriched_node)

    builder.set_entry_point("clean_profiles")

    builder.add_conditional_edges(
        "clean_profiles",
        lambda s: s.get("step"),
        {
            "profiles_cleaned" : "enrich_people",
            "clean_failed" : END
        }
    )

    builder.add_edge("enrich_people",    "enrich_companies")
    builder.add_edge("enrich_companies", "email_guess")
    builder.add_edge("email_guess",      "display_enriched")

    builder.add_conditional_edges(
        "display_enriched",
        lambda s : s.get("step"),
        {
            "enrichment_complete": END,
            "no_enriched_data" : END
        }
    )

    return builder.compile()