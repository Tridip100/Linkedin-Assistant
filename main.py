import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Agents"))

from Agents.agent_1.graph import build_graph
from Agents.agent_2.graph_2 import build_people_finder_graph
from Agents.agent_3.graph_3 import build_enrichment_graph

agent1 = build_graph()
agent2 = build_people_finder_graph()
agent3 = build_enrichment_graph()

# ── Initial state ──
initial_state = {
    # Agent 1
    "domain": "", "raw_text": "", "companies": [],
    "selected_company": None, "company_insights": None,
    "intent": {},

    # Agent 2
    "target_personas": {}, "raw_people_results": [],
    "discovered_people": [],

    # Agent 3
    "enriched_people": [], "enriched_companies": [],

    # Agent 4
    "scored_leads": [],

    # Agent 5
    "target_list": [],

    # Agent 6
    "generated_messages": [],

    # Control
    "messages": [], "error": None, "step": "start"
}

# ── Run Agent 1 ──
result1 = agent1.invoke(initial_state)

if result1.get("error"):
    print(f"\n❌ Agent 1 stopped: {result1.get('error')}")
    print(f"   Last step: {result1.get('step')}")
else:
    # ── Run Agent 2 ──
    result2 = agent2.invoke(result1)

    if result2.get("error"):
        print(f"\n❌ Agent 2 stopped: {result2.get('error')}")
        print(f"   Last step: {result2.get('step')}")

    else :
        result3 = agent3.invoke(result2)

        if result3.get("error"):
            print(f"\n❌ Agent 3 stopped: {result3.get('error')}")
            print(f"   Last step: {result3.get('step')}")