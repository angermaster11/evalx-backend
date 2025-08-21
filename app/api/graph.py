from langgraph.graph import StateGraph, END
from api.models.state import State
from api.nodes.idea import analyze_ppt_with_gpt

def router(state: State):
    mode = state["mode"]
    if mode == "ideation":
        return {"next_node": "docs_analyze"}
    elif mode == "code":
        return {"next_node": "code_analyze"}
    return {"next_node": END}


async def code_analyze(state: State) -> dict:
    # simple placeholder, must return dict
    return {"output": {"message": "Code analysis not implemented yet"}}


def build_graph():
    graph = StateGraph(State)

    graph.add_node("router", router)
    graph.add_node("docs_analyze", analyze_ppt_with_gpt)
    graph.add_node("code_analyze", code_analyze)

    # Add conditional edges based on the next_node value
    graph.add_conditional_edges(
        "router",
        lambda state: state.get("next_node", END),
        {
            "docs_analyze": "docs_analyze",
            "code_analyze": "code_analyze",
            END: END
        }
    )
    
    # Add edges from the processing nodes to END
    graph.add_edge("docs_analyze", END)
    graph.add_edge("code_analyze", END)
    
    graph.set_entry_point("router")
    return graph.compile()