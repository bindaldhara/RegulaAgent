"""LangGraph workflow: deterministic transitions with DENY / ESCALATE branches."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    action_node,
    audit_node,
    consent_node,
    identity_node,
    intent_node,
    policy_node,
    response_node,
    result_validation_node,
    tool_node,
)
from agent.state import AgentState
from schemas.enums import PolicyOutcome


def _route_after_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent and intent.is_emergency:
        return "policy"
    return "identity"


def _route_after_policy(state: AgentState) -> str:
    decision = state.get("policy_decision")
    if decision and decision.outcome == PolicyOutcome.ALLOW:
        return "tool"
    return "response"


def build_agent_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent_node)
    graph.add_node("identity", identity_node)
    graph.add_node("consent", consent_node)
    graph.add_node("action", action_node)
    graph.add_node("policy", policy_node)
    graph.add_node("tool", tool_node)
    graph.add_node("result_validation", result_validation_node)
    graph.add_node("response", response_node)
    graph.add_node("audit", audit_node)

    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", _route_after_intent, {"identity": "identity", "policy": "policy"})
    graph.add_edge("identity", "consent")
    graph.add_edge("consent", "action")
    graph.add_edge("action", "policy")
    graph.add_conditional_edges("policy", _route_after_policy, {"tool": "tool", "response": "response"})
    graph.add_edge("tool", "result_validation")
    graph.add_edge("result_validation", "response")
    graph.add_edge("response", "audit")
    graph.add_edge("audit", END)

    return graph.compile()


_agent_graph = None


def get_agent_workflow():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_workflow()
    return _agent_graph
