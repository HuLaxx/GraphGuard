"""Synthetic human review cases with signed identity and keyed audit chain.

This is a *local* analyst-demo workflow. SQLite append-only triggers and
per-event HMACs protect against accidental mutation and detect DB-only
tampering without the audit signing secret. Production requires external IAM,
key rotation, independent log anchoring, backup, retention and compliance.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import sqlite3

from ml.review.auth import ReviewAuthError, verify_demo_token
from ml.serving.verified_pit_scorer import (
    ScoringContractError, VerifiedSyntheticScorer, save_research_score,
)
from ml.explainability.verified_shap import (
    explain_transaction, save_research_explanation,
)

SCHEMA_VERSION = "synthetic-case-v1"
GENESIS = "0" * 64
VALID_ACTIONS = frozenset({
    "request_more_information", "escalate", "close_no_action", "close_review_complete",
})
FINAL_STATES = frozenset({"CLOSED_NO_ACTION", "CLOSED_REVIEW_COMPLETE"})
TRANSITIONS = {
    "OPEN": {
        "request_more_information": "NEEDS_INFORMATION",
        "escalate": "ESCALATED",
        "close_no_action": "CLOSED_NO_ACTION",
    },
    "NEEDS_INFORMATION": {
        "escalate": "ESCALATED", "close_no_action": "CLOSED_NO_ACTION",
    },
    "ESCALATED": {
        "close_no_action": "CLOSED_NO_ACTION",
        "close_review_complete": "CLOSED_REVIEW_COMPLETE",
    },
}
REQ_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{7,79}$")


class ReviewConflict(ValueError):
    pass


class ReviewIntegrityError(ValueError):
    pass


def _canonical(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mac(key: bytes, raw: str) -> str:
    return hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_request_id(value: str):
    if not isinstance(value, str) or not REQ_ID_RE.fullmatch(value):
        raise ReviewConflict("A unique 8-80-character idempotency key is required")


class SyntheticReviewStore:
    """Review-only store; every action requires a verified short-lived token.

    This class is used behind the local HTTP API; user ID/role never come
    from JSON request bodies. All state is derived from append-only events.
    """

    def __init__(self, connection: sqlite3.Connection, *,
                 scorer: VerifiedSyntheticScorer,
                 reviewer_signing_key: bytes, audit_signing_key: bytes):
        if not isinstance(scorer, VerifiedSyntheticScorer):
            raise ReviewIntegrityError("Trusted scorer required")
        if min(len(reviewer_signing_key), len(audit_signing_key)) < 32:
            raise ReviewAuthError("Reviewer and audit keys must be >=32 bytes")
        if hmac.compare_digest(reviewer_signing_key, audit_signing_key):
            raise ReviewAuthError("Independent audit and reviewer keys are required")
        self.conn = connection
        self.scorer = scorer
        self.reviewer_signing_key = reviewer_signing_key
        self.audit_signing_key = audit_signing_key
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript(
            """CREATE TABLE IF NOT EXISTS synthetic_review_cases (
                 case_id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL,
                 manifest_sha256 TEXT NOT NULL, anchor_json TEXT NOT NULL,
                 anchor_sha256 TEXT NOT NULL, anchor_mac TEXT NOT NULL,
                 created_at_utc TEXT NOT NULL,
                 UNIQUE(transaction_id, manifest_sha256)
               );
               CREATE TABLE IF NOT EXISTS synthetic_review_events (
                 case_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                 request_id TEXT NOT NULL, event_json TEXT NOT NULL,
                 event_sha256 TEXT NOT NULL, event_mac TEXT NOT NULL,
                 PRIMARY KEY(case_id, sequence),
                 UNIQUE(case_id, request_id),
                 FOREIGN KEY(case_id) REFERENCES synthetic_review_cases(case_id)
               );
               CREATE TRIGGER IF NOT EXISTS review_cases_no_update
                 BEFORE UPDATE ON synthetic_review_cases
                 BEGIN SELECT RAISE(ABORT,'review case immutable'); END;
               CREATE TRIGGER IF NOT EXISTS review_cases_no_delete
                 BEFORE DELETE ON synthetic_review_cases
                 BEGIN SELECT RAISE(ABORT,'review case immutable'); END;
               CREATE TRIGGER IF NOT EXISTS review_events_no_update
                 BEFORE UPDATE ON synthetic_review_events
                 BEGIN SELECT RAISE(ABORT,'review event immutable'); END;
               CREATE TRIGGER IF NOT EXISTS review_events_no_delete
                 BEFORE DELETE ON synthetic_review_events
                 BEGIN SELECT RAISE(ABORT,'review event immutable'); END;
            """
        )
        self.conn.commit()

    def _actor(self, signed_token: str) -> dict:
        return verify_demo_token(self.reviewer_signing_key, signed_token)

    def _evidence(self, txn: str) -> dict:
        # Retraining, source edits, model hash changes, missing model or missing
        # SHAP must all fail before a human case can be opened or changed.
        scored = self.scorer.score(self.conn, txn)
        explained = explain_transaction(self.conn, txn, scorer=self.scorer)
        if (
            explained["verified_model_probability"] != scored["score"]
            or explained["model_sha256"] != scored["model_sha256"]
            or explained["manifest_sha256"] != scored["manifest_sha256"]
            or explained["feature_snapshot_sha256"] != scored["feature_snapshot_sha256"]
            or explained["source_payload_sha256"] != scored["source_payload_sha256"]
        ):
            raise ReviewIntegrityError("Evidence score and explanation diverged")
        return {
            "transaction_id": txn,
            "manifest_sha256": scored["manifest_sha256"],
            "model_sha256": scored["model_sha256"],
            "source_payload_sha256": scored["source_payload_sha256"],
            "feature_snapshot_sha256": scored["feature_snapshot_sha256"],
            "explanation_sha256": explained["explanation_sha256"],
            "feature_version": scored["feature_version"],
            "model_input_version": scored["model_input_version"],
            "explainer_version": explained["explainer_version"],
            "score": scored["score"],
            "scope": "SYNTHETIC_ONLY_HUMAN_REVIEW_DEMO",
        }

    def _append(self, case_id: str, sequence: int, request_id: str,
                action: str, actor: dict, previous_sha256: str, state: str) -> dict:
        event = {
            "case_id": case_id, "sequence": sequence,
            "request_id": request_id,
            "action": action, "state_after": state,
            "reviewer_id": actor["subject"],
            "reviewer_role": actor["role"],
            "actor_token_jti": actor["jti"],  # token ID only, not token bytes
            "previous_event_sha256": previous_sha256,
            "created_at_utc": _now(),
            "schema_version": SCHEMA_VERSION,
        }
        raw = _canonical(event)
        self.conn.execute(
            """INSERT INTO synthetic_review_events
               (case_id, sequence, request_id, event_json, event_sha256, event_mac)
               VALUES(?,?,?,?,?,?)""",
            (case_id, sequence, request_id, raw, _sha(raw), _mac(self.audit_signing_key, raw)),
        )
        return event

    def _inspect(self, case_id: str, *, expected_evidence: dict | None = None) -> dict:
        row = self.conn.execute(
            """SELECT transaction_id, manifest_sha256, anchor_json,
                      anchor_sha256, anchor_mac FROM synthetic_review_cases
               WHERE case_id=?""",
            (case_id,),
        ).fetchone()
        if row is None:
            raise KeyError("Review case does not exist")
        txn, manifest, anchor_raw, anchor_sha, anchor_mac = row
        if (
            not hmac.compare_digest(_sha(anchor_raw), anchor_sha)
            or not hmac.compare_digest(_mac(self.audit_signing_key, anchor_raw), anchor_mac)
        ):
            raise ReviewIntegrityError("Review case anchor hash/MAC invalid")
        anchor = json.loads(anchor_raw)
        if (
            anchor.get("transaction_id") != txn
            or anchor.get("manifest_sha256") != manifest
            or anchor.get("scope") != "SYNTHETIC_ONLY_HUMAN_REVIEW_DEMO"
            or "explanation_sha256" not in anchor
        ):
            raise ReviewIntegrityError("Review anchor does not match case identity")
        if expected_evidence is not None and anchor != expected_evidence:
            raise ReviewIntegrityError("Persisted case evidence differs from verified source")
        rows = self.conn.execute(
            """SELECT sequence, request_id, event_json, event_sha256, event_mac
               FROM synthetic_review_events WHERE case_id=? ORDER BY sequence""",
            (case_id,),
        ).fetchall()
        if not rows:
            raise ReviewIntegrityError("Case has no opening audit event")
        state, prev = None, GENESIS
        events = []
        for index, (seq, request_id, raw, digest, mac) in enumerate(rows):
            if (
                seq != index
                or not hmac.compare_digest(_sha(raw), digest)
                or not hmac.compare_digest(_mac(self.audit_signing_key, raw), mac)
            ):
                raise ReviewIntegrityError("Audit chain hash, signature or sequence invalid")
            event = json.loads(raw)
            if (
                event.get("case_id") != case_id
                or event.get("sequence") != seq
                or event.get("request_id") != request_id
                or event.get("schema_version") != SCHEMA_VERSION
                or event.get("previous_event_sha256") != prev
                or not isinstance(event.get("reviewer_id"), str)
                or event.get("reviewer_role") not in {"analyst", "admin"}
            ):
                raise ReviewIntegrityError("Audit event identity or chain mismatch")
            action = event.get("action")
            if index == 0:
                if action != "case_opened" or event.get("state_after") != "OPEN":
                    raise ReviewIntegrityError("Invalid opening audit event")
                state = "OPEN"
            else:
                next_state = TRANSITIONS.get(state, {}).get(action)
                if (
                    next_state is None or next_state != event.get("state_after")
                    or (action.startswith("close_") and event["reviewer_role"] != "admin")
                ):
                    raise ReviewIntegrityError("Invalid audited transition or reviewer role")
                state = next_state
            prev = digest
            events.append(event)
        return {
            "case_id": case_id, "transaction_id": txn,
            "status": state, "version": len(events) - 1,
            "evidence": anchor,
            "audit_head_sha256": prev, "events": events,
        }

    def open_case(self, signed_token: str, transaction_id: str, *,
                  request_id: str) -> dict:
        actor = self._actor(signed_token)
        _require_request_id(request_id)
        evidence = self._evidence(transaction_id)
        # The source score and explanation persistence already verify their
        # own input/first-write provenance, but must happen before BEGIN.
        score = self.scorer.score(self.conn, transaction_id)
        save_research_score(self.conn, score, scorer=self.scorer)
        explanation = explain_transaction(self.conn, transaction_id, scorer=self.scorer)
        save_research_explanation(self.conn, explanation, scorer=self.scorer)
        case_id = "gg-" + _sha(transaction_id + "|" + evidence["manifest_sha256"])[:24]
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            found = self.conn.execute(
                "SELECT case_id FROM synthetic_review_cases WHERE case_id=?", (case_id,)
            ).fetchone()
            if found:
                existing = self._inspect(case_id, expected_evidence=evidence)
                first = existing["events"][0]
                if first["request_id"] != request_id or first["reviewer_id"] != actor["subject"]:
                    raise ReviewConflict("Case already exists; idempotent replay requires original actor and request")
                self.conn.commit()
                return existing
            anchor_raw = _canonical(evidence)
            self.conn.execute(
                """INSERT INTO synthetic_review_cases
                   (case_id, transaction_id, manifest_sha256, anchor_json,
                    anchor_sha256, anchor_mac, created_at_utc)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    case_id, transaction_id, evidence["manifest_sha256"],
                    anchor_raw, _sha(anchor_raw), _mac(self.audit_signing_key, anchor_raw), _now(),
                ),
            )
            self._append(case_id, 0, request_id, "case_opened", actor, GENESIS, "OPEN")
            view = self._inspect(case_id, expected_evidence=evidence)
            self.conn.commit()
            return view
        except Exception:
            self.conn.rollback()
            raise

    def get_case(self, signed_token: str, case_id: str) -> dict:
        self._actor(signed_token)
        view = self._inspect(case_id)
        verified = self._evidence(view["transaction_id"])
        if view["evidence"] != verified:
            raise ReviewIntegrityError("Case evidence no longer matches pinned model/source")
        return view

    def decide(self, signed_token: str, case_id: str, *, action: str,
               request_id: str, expected_version: int) -> dict:
        actor = self._actor(signed_token)
        _require_request_id(request_id)
        if action not in VALID_ACTIONS:
            raise ReviewConflict("Unknown research review action")
        if type(expected_version) is not int or expected_version < 0:
            raise ReviewConflict("Nonnegative expected review version required")
        if action.startswith("close_") and actor["role"] != "admin":
            raise ReviewAuthError("Only a demo admin can close a case")
        # Check source and model evidence before recording any human decision.
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            view = self._inspect(case_id)
            evidence = self._evidence(view["transaction_id"])
            if evidence != view["evidence"]:
                raise ReviewIntegrityError("Case evidence invalidated")
            existing = next((e for e in view["events"] if e["request_id"] == request_id), None)
            if existing is not None:
                if existing["reviewer_id"] == actor["subject"] and existing["action"] == action:
                    self.conn.commit()
                    return view
                raise ReviewConflict("Idempotency key reused for a different action/actor")
            if view["version"] != expected_version:
                raise ReviewConflict("Stale review version; refresh case before deciding")
            state = TRANSITIONS.get(view["status"], {}).get(action)
            if state is None:
                raise ReviewConflict("Invalid transition or case already closed")
            self._append(
                case_id, view["version"] + 1, request_id,
                action, actor, view["audit_head_sha256"], state,
            )
            changed = self._inspect(case_id, expected_evidence=evidence)
            self.conn.commit()
            return changed
        except Exception:
            self.conn.rollback()
            raise

    def session(self, signed_token: str) -> dict:
        """Verify identity server-side; return only safe demo role information."""
        actor = self._actor(signed_token)
        return {
            "subject": actor["subject"],
            "role": actor["role"],
            "scope": "SYNTHETIC_LOCAL_REVIEW_ONLY",
        }

    def list_cases(self, signed_token: str, *, limit: int = 25) -> dict:
        """Single-tenant synthetic queue; every case is integrity-checked.

        All signed demo reviewers can see all synthetic cases. This is NOT
        multi-tenant authorization and must not be deployed for real data.
        """
        self._actor(signed_token)
        if type(limit) is not int or limit < 1 or limit > 25:
            raise ReviewConflict("Invalid local case-list limit")
        ids = self.conn.execute(
            """SELECT case_id FROM synthetic_review_cases
               ORDER BY created_at_utc DESC, case_id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return {
            "scope": "SYNTHETIC_LOCAL_REVIEW_ONLY",
            "cases": [self.get_case(signed_token, row[0]) for row in ids],
        }

    def get_explanation(self, signed_token: str, case_id: str) -> dict:
        """Return real, reverified model-derived SHAP only for a saved case."""
        view = self.get_case(signed_token, case_id)
        explanation = explain_transaction(
            self.conn, view["transaction_id"], scorer=self.scorer,
        )
        evidence = view["evidence"]
        for key in (
            "manifest_sha256", "model_sha256", "source_payload_sha256",
            "feature_snapshot_sha256", "explanation_sha256",
        ):
            if explanation.get(key) != evidence.get(key):
                raise ReviewIntegrityError("Case explanation differs from evidence anchor")
        if explanation.get("verified_model_probability") != evidence.get("score"):
            raise ReviewIntegrityError("Case score and explanation differ")
        recorded = self.conn.execute(
            """SELECT explanation_json, explanation_sha256
               FROM transaction_research_explanations
               WHERE transaction_id=? AND manifest_sha256=? AND explainer_version=?""",
            (
                view["transaction_id"], evidence["manifest_sha256"],
                evidence["explainer_version"],
            ),
        ).fetchone()
        canonical = _canonical(explanation)
        if recorded != (canonical, _sha(canonical)):
            raise ReviewIntegrityError("Stored explanation differs from verified model")
        return explanation
