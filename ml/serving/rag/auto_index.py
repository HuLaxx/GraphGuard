"""
Auto-indexing utilities for RAG.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict

from ml.serving.rag.settings import get_rag_settings
from ml.serving.rag.router import get_rag_context
from ml.serving.rag.indexer import iter_repo_documents


def _run_indexing() -> Dict[str, int]:
    settings = get_rag_settings()
    ctx = get_rag_context()

    root_path = Path(settings.auto_index_root).resolve()
    documents = list(
        iter_repo_documents(
            root_path,
            settings.repo_include_exts,
            settings.repo_exclude_dirs,
            settings.repo_max_file_kb,
        )
    )

    if not documents:
        return {"files_indexed": 0, "indexed_chunks": 0}

    indexed_chunks = ctx.pipeline.ingest_documents(settings.auto_index_index, documents)
    return {"files_indexed": len(documents), "indexed_chunks": indexed_chunks}


def maybe_start_auto_indexing() -> None:
    settings = get_rag_settings()
    if not settings.enabled or not settings.auto_index_enabled:
        return

    if settings.auto_index_background:
        thread = threading.Thread(target=_run_indexing, daemon=True)
        thread.start()
    else:
        _run_indexing()
