from langgraph.graph import StateGraph, END
from core.state import AgentState
from .nodes_2 import (
    decide_targets_node,
    search_people_node,
    extract_people_node,
)

def build_people_finder_graph():
    builder = StateGraph(AgentState)

    # Nodes (ONLY what exists)
    builder.add_node("decide_targets", decide_targets_node)
    builder.add_node("search_people", search_people_node)
    builder.add_node("extract_people", extract_people_node)

    # Entry
    builder.set_entry_point("decide_targets")

    # 1️⃣ Decide Targets
    builder.add_conditional_edges(
        "decide_targets",
        lambda s: s.get("step"),
        {
            "targets_decided": "search_people",
            "targets_failed": END,
        },
    )

    # 2️⃣ Search People
    builder.add_conditional_edges(
        "search_people",
        lambda s: s.get("step"),
        {
            "people_search_done": "extract_people",
            "people_search_failed": END,
        },
    )

    # 3️⃣ Extract People (FINAL STEP)
    builder.add_conditional_edges(
        "extract_people",
        lambda s: s.get("step"),
        {
            "people_extracted": END,
            "extraction_failed": END,
        },
    )

    return builder.compile()