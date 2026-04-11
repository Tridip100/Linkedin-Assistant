from langgraph.graph import StateGraph, END
from core.state import AgentState
from .nodes import (
    domain_input_node,
    search_context_node,
    company_extraction_node,
    company_info_node,
)

def build_graph():
    builder = StateGraph(AgentState)

    # Nodes (ONLY existing ones)
    builder.add_node("domain_input", domain_input_node)
    builder.add_node("search_context", search_context_node)
    builder.add_node("company_extraction", company_extraction_node)
    builder.add_node("company_info", company_info_node)

    # Entry
    builder.set_entry_point("domain_input")

    # 1️⃣ Domain Input
    builder.add_conditional_edges(
        "domain_input",
        lambda s: s.get("step"),
        {
            "domain_captured": "search_context",
            "domain_failed": END,
        },
    )

    # 2️⃣ Search Context
    builder.add_conditional_edges(
        "search_context",
        lambda s: s.get("step"),
        {
            "context_fetched": "company_extraction",
            "context_failed": END,
        },
    )

    # 3️⃣ Company Extraction
    builder.add_conditional_edges(
        "company_extraction",
        lambda s: s.get("step"),
        {
            "companies_extracted": "company_info",  # direct flow (no UI node yet)
            "extraction_failed": END,
        },
    )

    # 4️⃣ Company Info (Final)
    builder.add_conditional_edges(
        "company_info",
        lambda s: s.get("step"),
        {
            "company_insights_generated": END,
            "company_info_failed": END,
        },
    )

    return builder.compile()