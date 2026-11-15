"""GraphGuard explainability tools.

Heavy optional SHAP, PyTorch/Graphviz and graph visualisation modules are
loaded only when explicitly used. CPU-only native XGBoost TreeSHAP must
not eagerly import the legacy visualisation stack.
"""
from importlib import import_module

__all__ = ["FraudExplainer", "GraphVisualizer"]

_EXPORTS = {
    "FraudExplainer": ".shap_analysis",
    "GraphVisualizer": ".graph_visualization",
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_EXPORTS[name], __name__), name)
    globals()[name] = value
    return value
