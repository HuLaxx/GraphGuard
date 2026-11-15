"""Inspect an accepted synthetic transaction with a pinned, trained model.

Example (use SHA pin copied from a trusted CI artifact, never guessed):
python -m ml.serving.score_pit_cli \
  --ledger .local/transaction-ledger.sqlite3 \
  --artifacts .local/ml-baselines \
  --trusted-manifest-sha256 <sha> \
  --transaction-id synthetic-example
"""
import argparse
import json
import sqlite3
from pathlib import Path

from ml.serving.verified_pit_scorer import (
    VerifiedSyntheticScorer, save_research_score,
)


def main():
    parser = argparse.ArgumentParser(
        description="SYNTHETIC ONLY: trust-pinned offline research scoring"
    )
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--trusted-manifest-sha256", required=True)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument(
        "--persist-research-score", action="store_true",
        help="Write append-only research score to local ledger (no automated decision)",
    )
    args = parser.parse_args()
    if not args.ledger.is_file():
        parser.error("Ledger must already exist; refusing to create an empty database")
    scorer = VerifiedSyntheticScorer(
        args.artifacts, expected_manifest_sha256=args.trusted_manifest_sha256,
    )
    with sqlite3.connect(f"file:{args.ledger.resolve()}?mode=rw", uri=True) as connection:
        score = scorer.score(connection, args.transaction_id)
        if args.persist_research_score:
            save_research_score(connection, score, scorer=scorer)
    print(json.dumps(score, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
