"""
app/agent/teacher_agent.py
───────────────────────────
LANGCHAIN CONCEPT: LangGraph + ReAct Agent Pattern
────────────────────────────────────────────────────
This is the heart of the app. The StateGraph wires all the nodes together.

LangGraph's StateGraph works like this:
  1. You define nodes (functions that read/write state)
  2. You add edges (which node leads to which)
  3. Conditional edges use the router function to decide at runtime
  4. You compile the graph → it becomes a runnable object
  5. You call graph.invoke(initial_state) or graph.stream(initial_state)

ReAct pattern = Reasoning + Acting loop:
  The agent THINKS about what to do, ACTS (calls a tool or generates output),
  OBSERVES the result, THINKS again, ACTS again... until done.

In code.teach the loop looks like:
  router → retrieve_context → give_task
         ↑                              ↓ (student submits code)
         └──── evaluate_code ←──────────┘
         ↑
         └──── handle_signal  (if student sends a signal)
         ↑
         └──── plan_lesson    (once at start)
         ↑
         └──── end_session    (when done)

Docs to read:
  https://langchain-ai.github.io/langgraph/concepts/
  https://langchain-ai.github.io/langgraph/how-tos/define-graph/
"""

from app.agent.state import TeachState, initial_state
from app.agent.nodes import (
    plan_lesson,
    retrieve_context,
    give_task,
    evaluate_code,
    handle_signal,
    prerequisite_check,
    update_profile,
    router_node,
    route_decision,
    end_session,
)
from app.chains.planner_chain import score_assessment, detect_topic_metadata
print("Debug: teacher_agent.py - Done importing nodes")

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


def build_graph():
    """
    Assembles and compiles the teaching agent graph.
    """
    graph = StateGraph(TeachState)

    graph.add_node("router",             router_node)
    graph.add_node("plan_lesson",        plan_lesson)
    graph.add_node("retrieve_context",   retrieve_context)
    graph.add_node("give_task",          give_task)
    graph.add_node("evaluate_code",      evaluate_code)
    graph.add_node("handle_signal",      handle_signal)
    graph.add_node("prerequisite_check", prerequisite_check)
    graph.add_node("update_profile",     update_profile)
    graph.add_node("end_session",        end_session)

    graph.set_entry_point("router")
    
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "plan_lesson":      "plan_lesson",
            "retrieve_context": "retrieve_context",
            "evaluate_code":    "evaluate_code",
            "handle_signal":    "handle_signal",
            "end_session":      "end_session",
        }
    )

    graph.add_edge("plan_lesson",        "router")
    graph.add_edge("retrieve_context",   "prerequisite_check")
    graph.add_edge("prerequisite_check", "give_task")
    graph.add_edge("give_task",          END)
    graph.add_edge("evaluate_code",      "update_profile")
    graph.add_edge("update_profile",     "router")
    graph.add_edge("handle_signal",      END)
    graph.add_edge("end_session",        END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ── Graph instance ────────────────────────────────────────────────────────────

teaching_graph = build_graph()


# ── Helper functions ──────────────────────────────────────────────────────────

def start_session(topic: str, level: str, assessment: list[dict] | None = None, thread_id: str = "default") -> dict:
    """
    Starts a new teaching session.
    Returns the first task.
    """
    profile = score_assessment(assessment) if assessment else None
    metadata = detect_topic_metadata(topic)
    state = initial_state(topic, level, profile=profile)
    state["topic_language"] = metadata.language
    state["topic_concept"] = metadata.concept
    config = {"configurable": {"thread_id": thread_id}}
    result = teaching_graph.invoke(state, config)
    return result["last_response"]


def submit_code(code: str, thread_id: str = "default") -> dict:
    """
    Handles a student submitting code.
    """
    state_update = {"student_code": code}
    config = {"configurable": {"thread_id": thread_id}}
    result = teaching_graph.invoke(state_update, config)
    return result["last_response"]


def send_signal(signal: str, detail: str = None, thread_id: str = "default") -> dict:
    """
    Handles a student clicking a signal button.
    """
    state_update = {"student_signal": signal, "signal_detail": detail}
    config = {"configurable": {"thread_id": thread_id}}
    result = teaching_graph.invoke(state_update, config)
    return result["last_response"]


def end_current_session(thread_id: str = "default") -> dict:
    """
    Triggers the end_session node.
    """
    state_update = {"should_end_session": True}
    config = {"configurable": {"thread_id": thread_id}}
    result = teaching_graph.invoke(state_update, config)
    return result.get("last_response")

