"""GraphGuard training entrypoints.

Heavy optional GAT, SMOTE, MLflow and Feast dependencies are imported only
when explicitly requested. Lightweight CPU-only baseline scripts must not
need the entire experimental ML stack just to import the package.
"""
from importlib import import_module

__all__ = [
    "XGBoostFraudModel",
    "FEATURE_COLUMNS",
    "FraudGAT",
    "GATTrainer",
    "EnsembleFraudModel",
]

_LEGACY_EXPORTS = {
    "XGBoostFraudModel": ".baseline_xgboost",
    "FEATURE_COLUMNS": ".baseline_xgboost",
    "FraudGAT": ".gat_model",
    "GATTrainer": ".gat_model",
    "EnsembleFraudModel": ".ensemble_model",
}


def __getattr__(name: str):
    """Preserve documented legacy exports without eager optional imports."""
    if name not in _LEGACY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_LEGACY_EXPORTS[name], package=__name__), name)
    globals()[name] = value
    return value
