"""Run the synthetic-only review API on localhost (never public bind).

Required environment: GRAPHGUARD_DEMO_REVIEW_KEY, GRAPHGUARD_DEMO_AUDIT_KEY,
GRAPHGUARD_LEDGER_PATH, GRAPHGUARD_MODEL_DIR, GRAPHGUARD_TRUSTED_MANIFEST_SHA256.
"""
import os
from pathlib import Path

import uvicorn

from ml.review.app import create_local_review_app


def main():
    required = [
        "GRAPHGUARD_DEMO_REVIEW_KEY", "GRAPHGUARD_DEMO_AUDIT_KEY",
        "GRAPHGUARD_LEDGER_PATH", "GRAPHGUARD_MODEL_DIR",
        "GRAPHGUARD_TRUSTED_MANIFEST_SHA256",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Required review configuration missing: " + ", ".join(missing))
    api = create_local_review_app(
        ledger_path=Path(os.environ["GRAPHGUARD_LEDGER_PATH"]),
        artifact_dir=Path(os.environ["GRAPHGUARD_MODEL_DIR"]),
        expected_manifest_sha256=os.environ["GRAPHGUARD_TRUSTED_MANIFEST_SHA256"],
        reviewer_signing_secret=os.environ["GRAPHGUARD_DEMO_REVIEW_KEY"],
        audit_signing_secret=os.environ["GRAPHGUARD_DEMO_AUDIT_KEY"],
    )
    uvicorn.run(api, host="127.0.0.1", port=8765, access_log=False)


if __name__ == "__main__":
    main()
