from langgraph.graph import StateGraph, END
from core.state import AgentState
from .nodes import (
    domain_input_node,
    search_context_node,
    company_extraction_node,
)


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("domain_input",        domain_input_node)
    builder.add_node("search_context",      search_context_node)
    builder.add_node("company_extraction",  company_extraction_node)

    builder.set_entry_point("domain_input")

    builder.add_conditional_edges(
        "domain_input",
        lambda s: s.get("step"),
        {
            "domain_captured": "search_context",
            "domain_failed":   END,
        }
    )

    builder.add_conditional_edges(
        "search_context",
        lambda s: s.get("step"),
        {
            "context_fetched": "company_extraction",
            "context_failed":  END,
        }
    )

    builder.add_conditional_edges(
        "company_extraction",
        lambda s: s.get("step"),
        {
            "companies_extracted": END,   # ← stop here, API returns companies to frontend
            "extraction_failed":   END,
        }
    )

    return builder.compile()