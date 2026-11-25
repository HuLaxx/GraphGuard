# ADR 002: LangGraph for Multi-Agent AI System

**Status:** Accepted  
**Date:** 2026-01-21  
**Deciders:** Engineering Team

## Context

Sentinance requires an AI system that can:
- Answer complex market intelligence questions
- Use multiple tools (get prices, analyze trends, calculate indicators)
- Provide step-by-step reasoning
- Integrate with LLMs (Gemini, GPT-4)

## Decision

Use **LangGraph** from LangChain for multi-agent orchestration instead of:
- Direct LLM API calls
- Custom state machine
- LangChain Agents (v1)

## Rationale

### Why LangGraph?

1. **Graph-Based Workflow**: Nodes (agents) + edges (transitions) = clear flow
2. **Stateful Execution**: `AgentState` persists across nodes
3. **Built-in Tools**: Tool calling with structured inputs/outputs
4. **Conditional Routing**: `should_continue` pattern for loops
5. **Production Ready**: Used by major AI applications

### Architecture

```
User Query
    │
    ▼
┌─────────────┐
│   Planner   │ ─── Breaks query into sub-tasks
└─────────────┘
    │
    ▼
┌─────────────┐
│ Researcher  │ ─── Executes tools (get_price, analyze_trend)
└─────────────┘
    │
    ▼
┌─────────────┐
│  Analyst    │ ─── Synthesizes insights via LLM
└─────────────┘
    │
    ▼
  Response
```

### Available Tools

```python
AVAILABLE_TOOLS = {
    "get_current_price": "Get real-time price for symbol",
    "analyze_trend": "Calculate trend direction and strength",
    "get_prediction": "Get ML price prediction",
    "get_indicators": "Get RSI, MACD, Bollinger Bands",
}
```

## Consequences

### Positive
- Clear separation of concerns (planning vs research vs analysis)
- Easy to add new tools
- Explainable AI (returns plan + reasoning)
- Integrates with any LLM backend (Gemini, OpenAI, etc.)

### Negative
- Additional dependency (langgraph, langchain)
- Debugging graph execution can be complex
- Requires understanding of state machines

## Implementation

```python
from langgraph.graph import StateGraph

# Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("analyst", analyst_node)

# Define edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "researcher")
workflow.add_edge("researcher", "analyst")
workflow.add_edge("analyst", END)

# Compile
agent = workflow.compile()
```

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Multi-Agent Systems](https://arxiv.org/abs/2308.00352)
