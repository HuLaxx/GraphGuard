"""Real Chromium acceptance of the LOCAL synthetic signed reviewer UI.

Uses real Next.js, FastAPI, frozen sklearn/XGBoost model, SHAP and SQLite.
Requires a loopback-only source fixture prepared by run_local_demo. This is
not a live bank, Kafka-backed web session, or a production identity system.
"""
import json
import os
import sqlite3
import time
from pathlib import Path
from urllib import request as http_request


def _signed_local_get(path: str, token: str) -> dict:
    req = http_request.Request(
        "http://127.0.0.1:8765/" + path,
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    with http_request.urlopen(req, timeout=10) as response:
        if response.status != 200:
            raise AssertionError("Signed local API returned non-success")
        return json.load(response)


def run_browser_acceptance(workspace: Path, processes, *, evidence_dir: Path) -> dict:
    from playwright.sync_api import expect, sync_playwright

    workspace = Path(workspace).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    if evidence_dir.is_symlink():
        raise RuntimeError("Refusing a symlinked evidence directory")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    tokens_path = workspace / "reviewer_tokens.json"
    if tokens_path.is_symlink():
        raise RuntimeError("Refusing symlinked private reviewer tokens")
    tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
    analyst, admin = tokens["analyst"], tokens["admin"]

    # Browser never sees local signing keys; token is passed only to a password
    # input and then to the same-origin, allowlisted Next.js review bridge.
    deadline = time.monotonic() + 140
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("Review service exited before browser acceptance")
        try:
            with http_request.urlopen("http://127.0.0.1:3000/cases", timeout=8) as resp:
                page = resp.read().decode("utf-8")
                if resp.status == 200 and "From a model signal" in page:
                    break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Real local Next case page did not become ready")

    before = _signed_local_get("cases", admin)
    assert before["scope"] == "SYNTHETIC_LOCAL_REVIEW_ONLY"
    assert len(before["cases"]) == 1
    original = before["cases"][0]
    assert original["status"] == "OPEN"
    assert original["transaction_id"] == "synthetic-ui-review-001"
    case_id = original["case_id"]
    model_hash = original["evidence"]["model_sha256"]
    source_hash = original["evidence"]["source_payload_sha256"]
    explanation_hash = original["evidence"]["explanation_sha256"]

    steps = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1365, "height": 900})
        page = context.new_page()
        page.goto("http://127.0.0.1:3000/cases", wait_until="domcontentloaded", timeout=120000)
        expect(page.get_by_text("Synthetic data only", exact=True).first).to_be_visible(timeout=30000)
        expect(page.get_by_role("heading", name="Connect your local review session")).to_be_visible()
        steps.append("real_browser_synthetic_only_labels")

        credential = page.get_by_label("Operator-issued reviewer token")
        credential.fill("invalid-signed-token")
        page.get_by_role("button", name="Verify signed session").click()
        expect(page.get_by_role("alert")).to_contain_text("401", timeout=20000)
        assert "Signed local session" not in page.locator("main").inner_text()
        steps.append("invalid_signed_token_denied")

        credential.fill(analyst)
        page.get_by_role("button", name="Verify signed session").click()
        expect(page.get_by_text("Signed local session · analyst.demo")).to_be_visible(timeout=30000)
        queue = page.get_by_role("region", name="Verified synthetic case queue")
        expect(queue.get_by_role("button")).to_have_count(1)
        queue.get_by_role("button").first.click()
        expect(page.get_by_role("region", name="Verified model attribution")).to_be_visible(timeout=30000)
        expect(page.get_by_role("region", name="Verified model attribution")).to_contain_text("all 12 features")
        expect(page.get_by_role("region", name="Verified case audit timeline")).to_be_visible()
        expect(page.get_by_text("Transaction: synthetic-ui-review-001")).to_be_visible()
        steps.append("signed_analyst_real_shap_and_audit_rendered")

        page.get_by_role("button", name="Escalate for review").click()
        expect(page.get_by_role("status")).to_contain_text("Human review event recorded", timeout=30000)
        after_escalation = _signed_local_get("cases/" + case_id, admin)
        assert after_escalation["status"] == "ESCALATED"
        assert after_escalation["version"] == 1
        assert after_escalation["audit_head_sha256"] != original["audit_head_sha256"]
        steps.append("analyst_browser_escalation_persisted")

        page.get_by_role("button", name="Disconnect").click()
        expect(page.get_by_role("heading", name="Connect your local review session")).to_be_visible()
        page.get_by_label("Operator-issued reviewer token").fill(admin)
        page.get_by_role("button", name="Verify signed session").click()
        expect(page.get_by_text("Signed local session · admin.demo")).to_be_visible(timeout=30000)
        page.get_by_role("region", name="Verified synthetic case queue").get_by_role("button").first.click()
        expect(page.get_by_role("region", name="Verified model attribution")).to_be_visible()
        page.get_by_role("button", name="Close — review complete").click()
        expect(page.get_by_role("status")).to_contain_text("Human review event recorded", timeout=30000)
        after_closure = _signed_local_get("cases/" + case_id, admin)
        assert after_closure["status"] == "CLOSED_REVIEW_COMPLETE"
        assert after_closure["version"] == 2
        assert [event["reviewer_role"] for event in after_closure["events"]] == [
            "analyst", "analyst", "admin"
        ]
        assert after_closure["audit_head_sha256"] != after_escalation["audit_head_sha256"]
        assert after_closure["evidence"] == original["evidence"]
        steps.append("admin_browser_closure_and_immutable_evidence")

        # Never persist credentials, cookies or local-storage tokens in artifacts.
        state = json.dumps(context.storage_state())
        html = page.content()
        assert all(token not in html and token not in state for token in (analyst, admin))
        screenshot = evidence_dir / "synthetic-review-final.png"
        page.screenshot(path=str(screenshot), full_page=True)
        steps.append("screenshot_without_credential_material")
        context.close()
        browser.close()

    ledger_path = workspace / "synthetic_ledger.sqlite3"
    with sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True) as db:
        rows = db.execute(
            "SELECT action FROM synthetic_review_events "
            "WHERE case_id=? ORDER BY sequence", (case_id,)
        ).fetchall()
    assert [row[0] for row in rows] == [
        "case_opened", "escalate", "close_review_complete"
    ]
    report = {
        "scope": "LOCAL_SYNTHETIC_BROWSER_ONLY_NOT_PRODUCTION",
        "steps": steps,
        "steps_passed": len(steps),
        "case_id": case_id,
        "transaction_id": original["transaction_id"],
        "source_sha256": source_hash,
        "model_sha256": model_hash,
        "shap_sha256": explanation_hash,
        "audit_head_sha256": after_closure["audit_head_sha256"],
        "final_status": after_closure["status"],
        "final_version": after_closure["version"],
        "backend": "local_FastAPI_SQLite_pinned_tabular_model_real_SHAP",
        "frontend": "real_Chromium_Next16_local_dev",
        "external_provider_calls": 0,
        "limitations": [
            "Browser fixture starts at synthetic accepted SQLite ledger, not real Kafka.",
            "Real Kafka-Neo4j to signed case is tested in a separate CI job.",
            "Demo HMAC tokens and local single-tenant reviewer are not enterprise OIDC.",
            "Model SHAP attribution is non-causal and not proof of fraud.",
            "No cloud backend, licensed fraud data or production performance claim.",
        ],
    }
    (evidence_dir / "synthetic-review-proof.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: real Chromium→signed Next bridge→FastAPI→SHAP→review audit", flush=True)
    return report
