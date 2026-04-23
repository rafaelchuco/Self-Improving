from __future__ import annotations

from copy import deepcopy

from agent.nodes.discovery import run_discovery
from agent.state import AgentState

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def build_graph():
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("discovery", run_discovery)
    graph.add_edge(START, "discovery")
    graph.add_edge("discovery", END)
    return graph.compile()


def execute_graph(initial_state: AgentState) -> AgentState:
    state = deepcopy(initial_state)
    runtime = dict(state.get("runtime", {}))

    graph = build_graph()
    if graph is not None:
        runtime["engine"] = "langgraph"
        state["runtime"] = runtime
        result = graph.invoke(state)
        result_runtime = dict(result.get("runtime", {}))
        result_runtime.setdefault("engine", "langgraph")
        result["runtime"] = result_runtime
        return result

    runtime["engine"] = "sequential_fallback"
    runtime["langgraph_available"] = False
    state["runtime"] = runtime

    update = run_discovery(state)
    state.update(update)

    notes = list(state.get("notes", []))
    notes.append("LangGraph not installed, sequential fallback used.")
    state["notes"] = notes
    return state
