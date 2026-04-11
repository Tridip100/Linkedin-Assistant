from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_6 import (
    build_sender_bio_node,
    generate_messages_node,
    quality_score_node,
    campaign_planner_node,
)


def build_message_generator_graph():
    builder = StateGraph(AgentState)

    builder.add_node("build_sender_bio",  build_sender_bio_node)
    builder.add_node("generate_messages", generate_messages_node)
    builder.add_node("quality_score",     quality_score_node)
    builder.add_node("campaign_planner",  campaign_planner_node)

    builder.set_entry_point("build_sender_bio")

    builder.add_conditional_edges(
        "build_sender_bio",
        lambda s: s.get("step"),
        {"profile_collected": "generate_messages", "profile_failed": END}
    )

    builder.add_edge("generate_messages", "quality_score")
    builder.add_edge("quality_score",     "campaign_planner")
    builder.add_edge("campaign_planner",  END)

    return builder.compile()