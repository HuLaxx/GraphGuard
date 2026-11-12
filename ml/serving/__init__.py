"""Model serving package.

The API is imported lazily so lightweight modules (such as the offline RAG
pipeline) can be tested without importing FastAPI, model-serving integrations
or a live runtime. Public package attributes remain backwards-compatible.
"""

from importlib import import_module

__all__ = ["app", "TransactionRequest", "PredictionResponse"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    api = import_module(".api", __name__)
    return getattr(api, name)
