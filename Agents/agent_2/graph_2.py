from langgraph.graph import StateGraph, END
from core.state import AgentState
from Agents.agent_2.nodes_2 import (
    decide_targets_node,
    search_people_node,
    extract_people_node,
    display_people_node,
)

def build_people_finder_graph():
    builder = StateGraph(AgentState)

    builder.add_node("decide_targets", decide_targets_node)
    builder.add_node("search_people",  search_people_node)
    builder.add_node("extract_people", extract_people_node)
    builder.add_node("display_people", display_people_node)

    builder.set_entry_point("decide_targets")

    builder.add_conditional_edges(
        "decide_targets",
        lambda s: s.get("step"),
        {"targets_decided": "search_people", "targets_failed": END}
    )

    builder.add_conditional_edges(
        "search_people",
        lambda s: s.get("step"),
        {"people_search_done": "extract_people", "people_search_failed": END}
    )

    builder.add_conditional_edges(
        "extract_people",
        lambda s: s.get("step"),
        {"people_extracted": "display_people", "extraction_failed": END}
    )

    builder.add_conditional_edges(
        "display_people",
        lambda s: s.get("step"),
        {"people_displayed": END, "no_people_found": END}
    )

    return builder.compile()