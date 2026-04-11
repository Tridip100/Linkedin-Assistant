from langgraph.graph import StateGraph, END
from core.state import AgentState
from Agents.agent_4.node_4 import (
    generate_questions_node,
    build_scoring_config_node,
    scoring_node,
)


def build_questions_graph():
    """Graph 4a — only generates questions"""
    builder = StateGraph(AgentState)

    builder.add_node("generate_questions", generate_questions_node)
    builder.set_entry_point("generate_questions")

    builder.add_conditional_edges(
        "generate_questions",
        lambda s: s.get("step"),
        {
            "questions_generated": END,
            "interview_failed":    END
        }
    )

    return builder.compile()


def build_scoring_graph():
    """Graph 4b — takes answers and scores leads"""
    builder = StateGraph(AgentState)

    builder.add_node("build_scoring_config", build_scoring_config_node)
    builder.add_node("scoring",              scoring_node)

    builder.set_entry_point("build_scoring_config")

    builder.add_conditional_edges(
        "build_scoring_config",
        lambda s: s.get("step"),
        {
            "config_built":  "scoring",
            "config_failed": END
        }
    )

    builder.add_edge("scoring", END)

    return builder.compile()