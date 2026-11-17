"""Signed local analyst review against actual synthetic score + native SHAP.

Proves reviewer roles, tamper/replay, optimistic conflicts, and API auth.
No real customer/case/production identity provider is claimed.
"""
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import time

from fastapi.testclient import TestClient
import pytest

from ml.training.pit_baselines import run_experiment
from ml.serving.verified_pit_scorer import VerifiedSyntheticScorer
from ml.review.auth import (
    ReviewAuthError, issue_demo_token, verify_demo_token,
)
from ml.review.app import create_local_review_app
from ml.review.case_store import (
    ReviewConflict, ReviewIntegrityError, SyntheticReviewStore,
)

CONSUMERS = Path(__file__).resolve().parents[2] / "data-eng" / "consumers"
sys.path.insert(0, str(CONSUMERS))
from transaction_ledger import TransactionLedger
from point_in_time_features import PointInTimeFeatureStore

T = 1_790_000_000_000
OPEN_REQUEST = "case-open-001"
ANALYST_REQUEST = "analyst-decision-001"
ADMIN_REQUEST = "admin-decision-001"


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    path = tmp_path_factory.mktemp("review-training")
    run_experiment(path, count=240, seed=42)
    digest = hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
    return path, digest


@pytest.fixture
def local_review(tmp_path, trained):
    model_path, pin = trained
    ledger_path = tmp_path / "review-ledger.sqlite3"
    ledger = TransactionLedger(str(ledger_path))
    store = PointInTimeFeatureStore(ledger.connection)
    rows = [
        dict(transaction_id="synthetic-review-history", timestamp=T - 3_600_000,
             amount=15.0),
        dict(transaction_id="synthetic-review-target", timestamp=T, amount=125.5),
    ]
    for i, item in enumerate(rows):
        txn = {
            **item, "user_id": "synthetic-review-user", "device_id": "synthetic-device",
            "merchant_id": "synthetic-merchant", "currency": "GBP",
            "schema_version": 1, "idempotency_key": "a" * 64,
        }
        assert ledger.record(txn, topic="synthetic.review", partition=0, offset=i).status == "new"
        store.snapshot_for(txn["transaction_id"])
    ledger.close()
    reviewer_secret = secrets.token_urlsafe(48)
    audit_secret = secrets.token_urlsafe(48)
    scorer = VerifiedSyntheticScorer(model_path, expected_manifest_sha256=pin)
    app = create_local_review_app(
        ledger_path=ledger_path,
        artifact_dir=model_path,
        expected_manifest_sha256=pin,
        reviewer_signing_secret=reviewer_secret,
        audit_signing_secret=audit_secret,
    )
    analyst_token = issue_demo_token(reviewer_secret.encode(), subject="analyst.one", role="analyst")
    admin_token = issue_demo_token(reviewer_secret.encode(), subject="admin.one", role="admin")
    intruder_token = issue_demo_token(reviewer_secret.encode(), subject="analyst.two", role="analyst")
    yield {
        "api": TestClient(app), "ledger": ledger_path, "model": scorer,
        "review_key": reviewer_secret.encode(), "audit_key": audit_secret.encode(),
        "analyst": analyst_token, "admin": admin_token, "other": intruder_token,
        "target": rows[-1]["transaction_id"],
    }


def headers(token):
    return {"Authorization": "Bearer " + token}


def open_case(fix, *, token=None, request=OPEN_REQUEST):
    response = fix["api"].post("/cases", headers=headers(token or fix["analyst"]),
                               json={"transaction_id": fix["target"], "request_id": request})
    assert response.status_code == 201, response.text
    return response.json()


def test_signed_token_expiry_signature_roles_and_wrong_audience(local_review):
    fix = local_review
    api = fix["api"]
    assert api.post("/cases", json={"transaction_id": fix["target"],
                                    "request_id": OPEN_REQUEST}).status_code == 401
    assert api.post("/cases", headers=headers("not-a-token"),
                    json={"transaction_id": fix["target"], "request_id": OPEN_REQUEST}).status_code == 401
    token = fix["analyst"]
    corrupted = token[:-2] + ("X" if token[-2] != "X" else "Y") + token[-1]
    assert api.post("/cases", headers=headers(corrupted),
                    json={"transaction_id": fix["target"], "request_id": OPEN_REQUEST}).status_code == 401
    old = issue_demo_token(
        fix["review_key"], subject="analyst.one", role="analyst",
        ttl=10, now=int(time.time()) - 100,
    )
    assert api.post("/cases", headers=headers(old),
                    json={"transaction_id": fix["target"], "request_id": OPEN_REQUEST}).status_code == 401
    with pytest.raises(ReviewAuthError, match="Invalid reviewer signature"):
        verify_demo_token(fix["audit_key"], fix["analyst"])
    with pytest.raises(ReviewAuthError, match="reviewer role"):
        issue_demo_token(fix["review_key"], subject="viewer", role="viewer")


def test_analyst_open_idempotency_role_checks_and_ordered_decision_audit(local_review):
    fix = local_review
    opened = open_case(fix)
    assert opened["status"] == "OPEN"
    assert opened["version"] == 0
    assert opened["events"][0]["action"] == "case_opened"
    assert opened["evidence"]["scope"] == "SYNTHETIC_ONLY_HUMAN_REVIEW_DEMO"
    assert len(opened["evidence"]["explanation_sha256"]) == 64
    assert len(opened["evidence"]["model_sha256"]) == 64
    assert len(opened["evidence"]["feature_snapshot_sha256"]) == 64
    assert open_case(fix) == opened

    read = fix["api"].get(f'/cases/{opened["case_id"]}', headers=headers(fix["other"]))
    assert read.status_code == 200
    assert read.json() == opened

    denied = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions', headers=headers(fix["analyst"]),
        json={"action": "close_no_action", "request_id": "close-too-early", "expected_version": 0},
    )
    assert denied.status_code == 403
    decision_body = {
        "action": "request_more_information",
        "request_id": ANALYST_REQUEST, "expected_version": 0,
    }
    first = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions',
        headers=headers(fix["analyst"]), json=decision_body,
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "NEEDS_INFORMATION"
    assert first.json()["version"] == 1
    assert len(first.json()["events"]) == 2
    # Retried request even with stale optimistic version is exactly idempotent.
    assert fix["api"].post(
        f'/cases/{opened["case_id"]}/actions',
        headers=headers(fix["analyst"]), json=decision_body,
    ).json() == first.json()
    stale = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions', headers=headers(fix["analyst"]),
        json={"action": "escalate", "request_id": "another-decision-001", "expected_version": 0},
    )
    assert stale.status_code == 409

    escalated = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions',
        headers=headers(fix["analyst"]),
        json={"action": "escalate", "request_id": "escalate-case-0001", "expected_version": 1},
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "ESCALATED"
    closed = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions',
        headers=headers(fix["admin"]),
        json={"action": "close_review_complete", "request_id": ADMIN_REQUEST,
              "expected_version": 2},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED_REVIEW_COMPLETE"
    assert closed.json()["version"] == 3
    assert [e["reviewer_role"] for e in closed.json()["events"]] == [
        "analyst", "analyst", "analyst", "admin",
    ]
    # Hard stop on actions after closure.
    refused = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions', headers=headers(fix["admin"]),
        json={"action": "escalate", "request_id": "after-close-001", "expected_version": 3},
    )
    assert refused.status_code == 409
    assert fix["api"].get(
        f'/cases/{opened["case_id"]}', headers=headers(fix["admin"])
    ).json() == closed.json()


def test_duplicate_case_requests_and_actor_spoofing_are_blocked(local_review):
    fix = local_review
    opened = open_case(fix)
    duplicate = fix["api"].post(
        "/cases", headers=headers(fix["other"]),
        json={"transaction_id": fix["target"], "request_id": OPEN_REQUEST},
    )
    assert duplicate.status_code == 409
    extra = fix["api"].post(
        "/cases", headers=headers(fix["analyst"]),
        json={"transaction_id": fix["target"], "request_id": "new-case-request"},
    )
    assert extra.status_code == 409
    spoofed = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions', headers=headers(fix["analyst"]),
        json={"action": "escalate", "request_id": "spoofer-0000001",
              "expected_version": 0, "role": "admin"},
    )
    assert spoofed.status_code == 422


def test_audit_records_are_immutable_and_keyed_tamper_is_detected(local_review):
    fix = local_review
    opened = open_case(fix)
    with sqlite3.connect(fix["ledger"]) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE synthetic_review_events SET event_json='{}' WHERE sequence=0"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM synthetic_review_cases WHERE case_id=?",
                (opened["case_id"],),
            )
        connection.rollback()
        # Simulate a privileged DB intruder who can DROP a trigger but
        # cannot access the separately injected HMAC audit key.
        connection.execute("DROP TRIGGER review_events_no_update")
        connection.execute(
            "UPDATE synthetic_review_events SET event_json='{}' WHERE sequence=0"
        )
        connection.commit()
    tampered = fix["api"].get(
        f'/cases/{opened["case_id"]}', headers=headers(fix["admin"]),
    )
    assert tampered.status_code == 409
    assert tampered.json()["detail"] == "Synthetic evidence integrity verification failed"


def test_changed_model_evidence_blocks_existing_case_decisions(local_review):
    fix = local_review
    opened = open_case(fix)
    with sqlite3.connect(fix["ledger"]) as connection:
        connection.execute(
            """UPDATE transaction_feature_snapshots SET features_sha256=?
               WHERE transaction_id=?""", ("f" * 64, fix["target"]),
        )
        connection.commit()
    change = fix["api"].post(
        f'/cases/{opened["case_id"]}/actions', headers=headers(fix["admin"]),
        json={"action": "close_no_action", "request_id": "blocked-close-001",
              "expected_version": 0},
    )
    assert change.status_code == 409


def test_local_server_fail_closed_without_secret_or_manifest_or_existing_ledger(
    tmp_path, trained,
):
    path, pin = trained
    with pytest.raises((ReviewAuthError, RuntimeError)):
        create_local_review_app(
            ledger_path=tmp_path / "missing.sqlite3",
            artifact_dir=path, expected_manifest_sha256=pin,
            reviewer_signing_secret="short", audit_signing_secret="different-short",
        )
    with pytest.raises(RuntimeError, match="Existing accepted"):
        create_local_review_app(
            ledger_path=tmp_path / "missing.sqlite3",
            artifact_dir=path, expected_manifest_sha256=pin,
            reviewer_signing_secret="a-long-test-secret-" * 3,
            audit_signing_secret="another-long-test-secret-" * 3,
        )


def test_provenance_retained_without_raw_secret_or_sensitive_payload(local_review):
    fix = local_review
    opened = open_case(fix)
    with sqlite3.connect(fix["ledger"]) as connection:
        rows = connection.execute(
            "SELECT event_json FROM synthetic_review_events"
        ).fetchall()
        raw = " ".join(row[0] for row in rows)
        assert "Bearer" not in raw
        assert fix["analyst"] not in raw
        assert "card_last4" not in raw and "ip_address" not in raw
        assert "synthetic_label" not in raw
        assert "jti" in raw
        assert "reviewer_id" in raw
        assert opened["audit_head_sha256"] == hashlib.sha256(rows[-1][0].encode()).hexdigest()



def test_signed_dashboard_session_list_and_exact_model_derived_shap(local_review):
    fix = local_review
    api = fix["api"]
    assert api.get("/session").status_code == 401
    assert api.get("/cases").status_code == 401
    assert api.get("/cases", headers=headers(fix["analyst"])).json() == {
        "scope": "SYNTHETIC_LOCAL_REVIEW_ONLY", "cases": [],
    }
    session = api.get("/session", headers=headers(fix["analyst"]))
    assert session.status_code == 200
    assert session.json() == {
        "subject": "analyst.one", "role": "analyst",
        "scope": "SYNTHETIC_LOCAL_REVIEW_ONLY",
    }
    opened = open_case(fix)
    listed = api.get("/cases", headers=headers(fix["other"]))
    assert listed.status_code == 200
    assert listed.json()["cases"] == [opened]
    explained = api.get(
        "/cases/" + opened["case_id"] + "/explanation",
        headers=headers(fix["admin"]),
    )
    assert explained.status_code == 200, explained.text
    payload = explained.json()
    assert payload["scope"] == "SYNTHETIC_ONLY_RESEARCH_EXPLANATION"
    assert payload["explanation_sha256"] == opened["evidence"]["explanation_sha256"]
    assert payload["model_sha256"] == opened["evidence"]["model_sha256"]
    assert payload["source_payload_sha256"] == opened["evidence"]["source_payload_sha256"]
    assert payload["feature_snapshot_sha256"] == opened["evidence"]["feature_snapshot_sha256"]
    assert payload["verified_model_probability"] == opened["evidence"]["score"]
    assert payload["reconstruction_abs_error"] <= 2e-5
    assert len(payload["all_features"]) == 12
    assert "not causal" in payload["non_causal_notice"].lower()
    assert api.get(
        "/cases/" + opened["case_id"] + "/explanation",
    ).status_code == 401


def test_dashboard_explanation_rejects_modified_research_record(local_review):
    fix = local_review
    opened = open_case(fix)
    with sqlite3.connect(fix["ledger"]) as connection:
        connection.execute(
            """UPDATE transaction_research_explanations
               SET explanation_json='{}'
               WHERE transaction_id=?""",
            (fix["target"],),
        )
        connection.commit()
    response = fix["api"].get(
        "/cases/" + opened["case_id"] + "/explanation",
        headers=headers(fix["analyst"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Synthetic evidence integrity verification failed"


def test_dashboard_list_requires_signed_token_and_returns_verified_case_only(local_review):
    fix = local_review
    opened = open_case(fix)
    assert fix["api"].get(
        "/cases", headers=headers("wrong-token"),
    ).status_code == 401
    with sqlite3.connect(fix["ledger"]) as connection:
        connection.execute(
            "UPDATE transaction_feature_snapshots SET features_sha256=? WHERE transaction_id=?",
            ("b" * 64, fix["target"]),
        )
        connection.commit()
    rejected = fix["api"].get(
        "/cases", headers=headers(fix["analyst"]),
    )
    assert rejected.status_code == 409
    assert opened["status"] == "OPEN"



def test_one_command_demo_seed_is_private_and_creates_actual_verified_case(tmp_path):
    from ml.review.seed_local_demo import prepare_demo
    workspace = tmp_path / "signed-demo"
    report = prepare_demo(workspace)
    assert report["synthetic_cases"] == 1
    assert report["unopened_synthetic_transaction"] == "synthetic-ui-review-002"
    assert "bypasses Kafka" in report["note"]
    private_file = workspace / "private_config.json"
    tokens_file = workspace / "reviewer_tokens.json"
    assert private_file.is_file() and tokens_file.is_file()
    assert private_file.stat().st_mode & 0o077 == 0
    assert tokens_file.stat().st_mode & 0o077 == 0
    config = json.loads(private_file.read_text())
    tokens = json.loads(tokens_file.read_text())
    assert config["GRAPHGUARD_DEMO_REVIEW_KEY"] != config["GRAPHGUARD_DEMO_AUDIT_KEY"]
    assert report["model_manifest_sha256"] == config["GRAPHGUARD_TRUSTED_MANIFEST_SHA256"]
    assert verify_demo_token(
        config["GRAPHGUARD_DEMO_REVIEW_KEY"].encode(), tokens["analyst"],
    )["role"] == "analyst"
    assert verify_demo_token(
        config["GRAPHGUARD_DEMO_REVIEW_KEY"].encode(), tokens["admin"],
    )["role"] == "admin"
    app = create_local_review_app(
        ledger_path=Path(config["GRAPHGUARD_LEDGER_PATH"]),
        artifact_dir=Path(config["GRAPHGUARD_MODEL_DIR"]),
        expected_manifest_sha256=config["GRAPHGUARD_TRUSTED_MANIFEST_SHA256"],
        reviewer_signing_secret=config["GRAPHGUARD_DEMO_REVIEW_KEY"],
        audit_signing_secret=config["GRAPHGUARD_DEMO_AUDIT_KEY"],
    )
    client = TestClient(app)
    queue = client.get("/cases", headers=headers(tokens["analyst"]))
    assert queue.status_code == 200, queue.text
    assert queue.json()["cases"][0]["case_id"] == report["case_id"]
    explained = client.get(
        "/cases/" + report["case_id"] + "/explanation",
        headers=headers(tokens["analyst"]),
    )
    assert explained.status_code == 200, explained.text
    assert explained.json()["explanation_sha256"] == (
        queue.json()["cases"][0]["evidence"]["explanation_sha256"]
    )
    # The workspace contains a *second* accepted event that can be reviewed.
    created = client.post(
        "/cases", headers=headers(tokens["analyst"]),
        json={
            "transaction_id": report["unopened_synthetic_transaction"],
            "request_id": "second-review-fixture-0001",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "OPEN"
    with pytest.raises(FileExistsError):
        prepare_demo(workspace)


def test_private_demo_tokens_can_refresh_without_exposing_signing_secrets(tmp_path):
    from ml.review.seed_local_demo import prepare_demo
    from ml.review.run_local_demo import _refresh_private_tokens
    workspace = tmp_path / "rotatable-demo"
    prepare_demo(workspace)
    config = json.loads((workspace / "private_config.json").read_text())
    original = json.loads((workspace / "reviewer_tokens.json").read_text())
    _refresh_private_tokens(workspace, config["GRAPHGUARD_DEMO_REVIEW_KEY"])
    regenerated = json.loads((workspace / "reviewer_tokens.json").read_text())
    assert regenerated["analyst"] != original["analyst"]
    assert (workspace / "reviewer_tokens.json").stat().st_mode & 0o077 == 0
    assert config["GRAPHGUARD_DEMO_REVIEW_KEY"] not in json.dumps(regenerated)
