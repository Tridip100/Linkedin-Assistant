from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_4 import (
    priority_interview_node,
    scoring_node,
    display_scores_node,
)


def build_scoring_graph():
    builder = StateGraph(AgentState)

    builder.add_node("priority_interview", priority_interview_node)
    builder.add_node("scoring",            scoring_node)
    builder.add_node("display_scores",     display_scores_node)

    builder.set_entry_point("priority_interview")

    builder.add_conditional_edges(
        "priority_interview",
        lambda s: s.get("step"),
        {
            "interview_done":   "scoring",
            "interview_failed": END
        }
    )

    builder.add_edge("scoring", "display_scores")

    builder.add_conditional_edges(
        "display_scores",
        lambda s: s.get("step"),
        {
            "scores_displayed": END,
            "no_scored_leads":  END
        }
    )

    return builder.compile()