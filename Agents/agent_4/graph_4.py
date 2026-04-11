from langgraph.graph import StateGraph, END
from core.state import AgentState
from .node_4 import (
    generate_questions_node,
    build_scoring_config_node,
    scoring_node,
)


def build_scoring_graph():
    builder = StateGraph(AgentState)

    builder.add_node("generate_questions",    generate_questions_node)
    builder.add_node("build_scoring_config",  build_scoring_config_node)
    builder.add_node("scoring",               scoring_node)

    builder.set_entry_point("generate_questions")

    builder.add_conditional_edges(
        "generate_questions",
        lambda s: s.get("step"),
        {"questions_generated": "build_scoring_config", "interview_failed": END}
    )

    builder.add_conditional_edges(
        "build_scoring_config",
        lambda s: s.get("step"),
        {"config_built": "scoring", "config_failed": END}
    )

    builder.add_edge("scoring", END)

    return builder.compile()