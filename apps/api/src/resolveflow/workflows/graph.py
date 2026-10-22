"""Real LangGraph transitions: bounded straight-line workers with conditional failure exits."""

from langgraph.graph import END, START, StateGraph

from resolveflow.workflows.contracts import STAGES, WorkflowState


def build_graph(workers, checkpointer):
    graph = StateGraph(WorkflowState)
    for stage in STAGES:
        graph.add_node(stage, workers.wrap(stage, getattr(workers, stage)))
    graph.add_edge(START, STAGES[0])
    for index, stage in enumerate(STAGES):
        next_stage = STAGES[index + 1] if index + 1 < len(STAGES) else END

        def route(state, target=next_stage):
            return END if state.get("status") in {"failed", "cancelled"} else target

        graph.add_conditional_edges(stage, route, [END] if next_stage == END else [next_stage, END])
    return graph.compile(checkpointer=checkpointer)
