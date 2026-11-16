"""Operator only: mint a short-lived signed demo review token.

Never expose this action through FastAPI, and never commit or log its secret.
Requires GRAPHGUARD_DEMO_REVIEW_KEY from a local secret store.
"""
import argparse
import os

from ml.review.auth import checked_key, issue_demo_token


def main():
    parser = argparse.ArgumentParser(description="Local synthetic reviewer token issuer")
    parser.add_argument("--subject", required=True, help="Non-sensitive synthetic reviewer ID")
    parser.add_argument("--role", required=True, choices=("analyst", "admin"))
    parser.add_argument("--ttl-seconds", type=int, default=600)
    args = parser.parse_args()
    key = checked_key(os.environ.get("GRAPHGUARD_DEMO_REVIEW_KEY", ""), "Review signing key")
    token = issue_demo_token(
        key, subject=args.subject, role=args.role, ttl=args.ttl_seconds,
    )
    print(token)  # A bearer secret: don't paste into logs, screenshots or Git.


if __name__ == "__main__":
    main()
