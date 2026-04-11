from langgraph.graph import StateGraph, END
from core.state import AgentState
from .nodes import *

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("domain_input", domain_input_node)
    builder.add_node("search_context", search_context_node)
    builder.add_node("company_extraction", company_extraction_node)
    builder.add_node("display", display_companies_node)
    builder.add_node("select", user_selection_node)
    builder.add_node("info", company_info_node)

    builder.set_entry_point("domain_input")

    builder.add_edge("domain_input", "search_context")

    # If search fails, stop — don't loop
    builder.add_conditional_edges(
        "search_context",
        lambda state: state.get("step"),
        {
            "context_fetched": "company_extraction",
            "context_failed": END          # ← stop if Serper fails
        }
    )

    # If extraction fails, stop — don't loop
    builder.add_conditional_edges(
        "company_extraction",
        lambda state: state.get("step"),
        {
            "companies_extracted": "display",
            "extraction_failed": END        # ← stop if LLM JSON fails
        }
    )

    builder.add_conditional_edges(
        "display",
        lambda state: state.get("step"),
        {
            "companies_displayed": "select",
            "no_companies": END             # ← stop, don't loop back
        }
    )

    builder.add_conditional_edges(
        "select",
        lambda state: state.get("step"),
        {
            "company_selected": "info",
            "selection_failed": "display"
        }
    )

    builder.add_conditional_edges(
        "info",
        lambda state: state.get("step"),
        {
            "company_insights_generated": END,
            "company_info_failed": "select"
        }
    )

    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()

    state = {
        "domain": "",
        "raw_text": "",
        "companies": [],
        "selected_company": None,
        "company_insights": None,
        "messages": [],
        "error": None,
        "step": "start"
    }

    result = graph.invoke(state)

    # Show error if graph ended early
    if result.get("error"):
        print(f"\n❌ Stopped: {result.get('error')}")
        print(f"   Last step: {result.get('step')}")