"""Compile the deterministic LangGraph workflow with no supervisor routing."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from ir_copilot.config import AppSettings

from .llm import OpenAIStructuredLLM, StructuredLLM, UnavailableLLM
from .nodes import correlate, gate_on_anomaly, hypothesize, remediate
from .state import IncidentState
from .tools import ToolContext


@dataclass(frozen=True)
class GraphDependencies:
    tools: ToolContext
    llm: StructuredLLM
    settings: AppSettings


def default_llm(settings: AppSettings) -> StructuredLLM:
    if not settings.openai_api_key:
        return UnavailableLLM()
    return OpenAIStructuredLLM(settings.openai_api_key, settings.openai_model)


def build_graph(dependencies: GraphDependencies):
    """Build gate → correlate → hypothesize → remediate with deterministic edges."""
    graph = StateGraph(IncidentState)
    graph.add_node("gate_on_anomaly", gate_on_anomaly)
    graph.add_node("correlate", correlate(dependencies.tools))
    graph.add_node("hypothesize", hypothesize(dependencies.llm, dependencies.settings.max_llm_calls_per_run))
    graph.add_node("remediate", remediate(dependencies.tools, dependencies.llm, dependencies.settings.max_llm_calls_per_run))
    graph.add_edge(START, "gate_on_anomaly")
    graph.add_conditional_edges(
        "gate_on_anomaly",
        lambda state: END if state.get("status") == "skipped" else "correlate",
    )
    graph.add_edge("correlate", "hypothesize")
    graph.add_conditional_edges(
        "hypothesize",
        lambda state: END if state.get("error") else "remediate",
    )
    graph.add_edge("remediate", END)
    return graph.compile()
