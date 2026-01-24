"""
Indexing utilities for RAG.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from ml.serving.rag.pipeline import RagDocument


@dataclass
class RepoIngestResult:
    files_indexed: int
    chunks_added: int
    skipped_files: int


def iter_repo_documents(
    root: Path,
    include_exts: List[str],
    exclude_dirs: List[str],
    max_file_kb: int,
) -> Iterable[RagDocument]:
    root = root.resolve()
    exclude_set = {d.lower() for d in exclude_dirs}
    include_set = {ext.lower() for ext in include_exts}

    for path in root.rglob("*"):
        if path.is_dir():
            if path.name.lower() in exclude_set:
                continue
            continue

        if path.suffix.lower() not in include_set:
            continue

        if any(part.lower() in exclude_set for part in path.parts):
            continue

        try:
            size_kb = path.stat().st_size / 1024
        except OSError:
            continue

        if size_kb > max_file_kb:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = path.relative_to(root)
        yield RagDocument(
            id=str(rel_path),
            text=text,
            metadata={
                "source": str(rel_path),
                "size_kb": round(size_kb, 2),
            },
        )


def count_repo_documents(
    root: Path,
    include_exts: List[str],
    exclude_dirs: List[str],
    max_file_kb: int,
) -> Dict[str, int]:
    files = 0
    skipped = 0
    exclude_set = {d.lower() for d in exclude_dirs}
    include_set = {ext.lower() for ext in include_exts}
    for path in root.rglob("*"):
        if path.is_dir():
            if path.name.lower() in exclude_set:
                continue
            continue

        if path.suffix.lower() not in include_set:
            skipped += 1
            continue
        try:
            size_kb = path.stat().st_size / 1024
        except OSError:
            skipped += 1
            continue

        if size_kb > max_file_kb:
            skipped += 1
            continue

        if any(part.lower() in exclude_set for part in path.parts):
            skipped += 1
            continue

        files += 1

    return {"files": files, "skipped": skipped}
