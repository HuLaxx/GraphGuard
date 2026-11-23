"""Loopback-only synthetic analyst API (not a production identity provider).

Every endpoint verifies short-lived, externally minted demo review tokens.
Do not mount or expose this service on a public network.
"""
from pathlib import Path
import sqlite3

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from ml.review.auth import ReviewAuthError, checked_key
from ml.review.case_store import ReviewConflict, ReviewIntegrityError, SyntheticReviewStore
from ml.serving.verified_pit_scorer import ScoringContractError, VerifiedSyntheticScorer

bearer = HTTPBearer(auto_error=False)


class CreateCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=8, max_length=80)


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["request_more_information", "escalate", "close_no_action", "close_review_complete"]
    request_id: str = Field(min_length=8, max_length=80)
    expected_version: int = Field(ge=0)


def create_local_review_app(*, ledger_path: Path, artifact_dir: Path,
                            expected_manifest_sha256: str,
                            reviewer_signing_secret: str,
                            audit_signing_secret: str) -> FastAPI:
    signing_key = checked_key(reviewer_signing_secret, "Reviewer signing key")
    audit_key = checked_key(audit_signing_secret, "Audit signing key")
    if signing_key == audit_key:
        raise RuntimeError("Review and audit secrets must be different")
    if not Path(ledger_path).is_file():
        raise RuntimeError("Existing accepted synthetic SQLite ledger required")
    scorer = VerifiedSyntheticScorer(
        artifact_dir, expected_manifest_sha256=expected_manifest_sha256,
    )
    api = FastAPI(
        title="GraphGuard Synthetic Review Demo",
        description="Loopback-only, signed reviewer token, research evidence; not production fraud decisions",
        version="0.1-local-demo",
    )

    def review_token(credentials: HTTPAuthorizationCredentials | None = Security(bearer)) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Signed reviewer Bearer token required")
        return credentials.credentials

    def store():
        # SQLite is local and one-writer; separate per-request connection.
        connection = sqlite3.connect(
            f"file:{Path(ledger_path).resolve()}?mode=rw", uri=True,
            timeout=10, check_same_thread=False,
        )
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield SyntheticReviewStore(
                connection, scorer=scorer,
                reviewer_signing_key=signing_key, audit_signing_key=audit_key,
            )
        finally:
            connection.close()

    @api.exception_handler(ReviewAuthError)
    async def auth_error(_, exc: ReviewAuthError):
        from fastapi.responses import JSONResponse
        code = 403 if "Only a demo admin" in str(exc) else 401
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    @api.exception_handler(ReviewConflict)
    async def conflict_error(_, exc: ReviewConflict):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @api.exception_handler(ReviewIntegrityError)
    async def integrity_error(_, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail": "Synthetic evidence integrity verification failed"})

    @api.exception_handler(ScoringContractError)
    async def scoring_error(_, exc: ScoringContractError):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail": "Synthetic evidence verification failed"})

    @api.get("/health")
    def health():
        # No model weights, secret, actor, ledger or case data in health.
        return {"status": "local-synthetic-review-only", "operational": False}

    @api.get("/session")
    def session(token: str = Depends(review_token),
                db: SyntheticReviewStore = Depends(store)):
        return db.session(token)

    @api.get("/cases")
    def list_cases(token: str = Depends(review_token),
                   db: SyntheticReviewStore = Depends(store)):
        return db.list_cases(token)

    @api.get("/cases/{case_id}/explanation")
    def get_explanation(case_id: str, token: str = Depends(review_token),
                        db: SyntheticReviewStore = Depends(store)):
        try:
            return db.get_explanation(token, case_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Case not found")

    @api.post("/cases", status_code=201)
    def create_case(body: CreateCase, token: str = Depends(review_token),
                    db: SyntheticReviewStore = Depends(store)):
        try:
            return db.open_case(token, body.transaction_id, request_id=body.request_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown accepted synthetic source")

    @api.get("/cases/{case_id}")
    def get_case(case_id: str, token: str = Depends(review_token),
                 db: SyntheticReviewStore = Depends(store)):
        try:
            return db.get_case(token, case_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Case not found")

    @api.post("/cases/{case_id}/actions")
    def decide(case_id: str, body: ReviewAction, token: str = Depends(review_token),
               db: SyntheticReviewStore = Depends(store)):
        try:
            return db.decide(
                token, case_id, action=body.action,
                request_id=body.request_id, expected_version=body.expected_version,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Case not found")

    return api
