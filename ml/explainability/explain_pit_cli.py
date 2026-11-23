"""SYNTHETIC ONLY: trustworthy local SHAP explanation, no API/deployment.

Use the manifest pin obtained independently from trusted CI artifacts.
Prints numerical research attributions, never operational fraud decisions.
"""
import argparse
import json
import sqlite3
from pathlib import Path

from ml.serving.verified_pit_scorer import (
    VerifiedSyntheticScorer, save_research_score,
)
from ml.explainability.verified_shap import (
    explain_transaction, save_research_explanation,
)


def main():
    parser = argparse.ArgumentParser(
        description="Research-only SHAP on a hash-verified synthetic scorer"
    )
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--trusted-manifest-sha256", required=True)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--persist-research-artifacts", action="store_true",
        help="Save verified score and SHAP locally (not an analyst decision)",
    )
    args = parser.parse_args()
    if not args.ledger.is_file():
        parser.error("Source ledger must already exist")
    scorer = VerifiedSyntheticScorer(
        args.artifacts, expected_manifest_sha256=args.trusted_manifest_sha256,
    )
    with sqlite3.connect(f"file:{args.ledger.resolve()}?mode=rw", uri=True) as conn:
        explanation = explain_transaction(
            conn, args.transaction_id, scorer=scorer, top_k=args.top_k,
        )
        if args.persist_research_artifacts:
            score = scorer.score(conn, args.transaction_id)
            save_research_score(conn, score, scorer=scorer)
            save_research_explanation(conn, explanation, scorer=scorer)
    print(json.dumps(explanation, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
