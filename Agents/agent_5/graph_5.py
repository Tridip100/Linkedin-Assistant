from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_5 import (
    filter_targets_node,
    email_verify_node,
    shortlist_node,
    build_dashboard_node,
)


def build_targeting_graph():
    builder = StateGraph(AgentState)

    builder.add_node("filter_targets",  filter_targets_node)
    builder.add_node("email_verify",    email_verify_node)
    builder.add_node("shortlist",       shortlist_node)
    builder.add_node("build_dashboard", build_dashboard_node)

    builder.set_entry_point("filter_targets")

    builder.add_conditional_edges(
        "filter_targets",
        lambda s: s.get("step"),
        {"targets_filtered": "email_verify", "filter_failed": END}
    )

    builder.add_edge("email_verify",    "shortlist")
    builder.add_edge("shortlist",       "build_dashboard")
    builder.add_edge("build_dashboard", END)

    return builder.compile()