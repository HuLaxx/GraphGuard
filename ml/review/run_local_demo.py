"""One command to seed and run the LOCAL-only synthetic reviewer demo.

After installing Python requirements and frontend npm dependencies:
python -m ml.review.run_local_demo
Ctrl-C terminates the local API and Next development server.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
from urllib import request as http_request

from ml.review.auth import issue_demo_token
from ml.review.seed_local_demo import prepare_demo

ROOT = Path(__file__).resolve().parents[2]


def _refresh_private_tokens(workspace: Path, review_secret: str):
    # Local demo bearer tokens expire quickly. Never print them or put them
    # in CLI arguments, URLs, GitHub workflow logs or browser storage.
    payload = {
        "analyst": issue_demo_token(
            review_secret.encode(), subject="analyst.demo", role="analyst",
        ),
        "admin": issue_demo_token(
            review_secret.encode(), subject="admin.demo", role="admin",
        ),
        "notice": "PRIVATE: 600s local demo bearer tokens. Never share or commit.",
    }
    target = workspace / "reviewer_tokens.json"
    if target.is_symlink():
        raise RuntimeError("Refusing to overwrite a symlink as private tokens")
    temporary = workspace / ("." + secrets.token_hex(12) + ".json")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _request_json(path: str, token: str, *, body: dict | None = None) -> dict:
    req = http_request.Request(
        "http://127.0.0.1:3000/review-local/" + path,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            **({} if body is None else {"Content-Type": "application/json"}),
        },
        method="GET" if body is None else "POST",
    )
    with http_request.urlopen(req, timeout=10) as response:
        if response.status not in (200, 201):
            raise RuntimeError("Local review HTTP smoke returned non-success")
        return json.load(response)


def _smoke_browser_proxy(workspace: Path, processes):
    """Real loopback HTTP proof of Next route + signed API + native SHAP.

    This is NOT a full browser automation or Kafka-backed UI smoke test.
    """
    token = json.loads(
        (workspace / "reviewer_tokens.json").read_text(encoding="utf-8")
    )["analyst"]
    deadline = time.monotonic() + 150
    ready = False
    last_failure = "local services not ready"
    while time.monotonic() < deadline:
        if any(proc.poll() is not None for proc in processes):
            raise RuntimeError("Local review service exited before HTTP smoke")
        try:
            with http_request.urlopen("http://127.0.0.1:3000/cases", timeout=6) as response:
                html = response.read().decode("utf-8")
                if response.status != 200 or "From a model signal" not in html:
                    raise RuntimeError("Signed case page not rendered")
            who = _request_json("session", token)
            if who["scope"] != "SYNTHETIC_LOCAL_REVIEW_ONLY" or who["role"] != "analyst":
                raise RuntimeError("Signed reviewer identity differs from seed")
            ready = True
            break
        except Exception as error:
            last_failure = type(error).__name__
            time.sleep(1)
    if not ready:
        raise RuntimeError("Loopback Next+FastAPI startup smoke failed: " + last_failure)

    listing = _request_json("cases", token)
    if len(listing.get("cases", [])) != 1:
        raise RuntimeError("Seeded synthetic case queue differs")
    case = listing["cases"][0]
    explanation = _request_json("cases/" + case["case_id"] + "/explanation", token)
    if (
        explanation["explanation_sha256"] != case["evidence"]["explanation_sha256"]
        or explanation["model_sha256"] != case["evidence"]["model_sha256"]
        or explanation["verified_model_probability"] != case["evidence"]["score"]
        or len(explanation["all_features"]) != 12
    ):
        raise RuntimeError("Native model explanation is not the saved case evidence")
    updated = _request_json("cases/" + case["case_id"] + "/actions", token, body={
        "action": "escalate", "request_id": "http-demo-smoke-escalate-001",
        "expected_version": 0,
    })
    if updated["status"] != "ESCALATED" or updated["version"] != 1:
        raise RuntimeError("Signed HTTP review state transition failed")
    reloaded = _request_json("cases/" + case["case_id"], token)
    if reloaded["audit_head_sha256"] != updated["audit_head_sha256"]:
        raise RuntimeError("Signed review audit was not persisted")
    print("PASS: actual local Next case page → signed API → SHAP → human review audit", flush=True)


def run_local(workspace: Path, *, smoke: bool = False, browser_smoke: bool = False,
              evidence_dir: Path | None = None,
              expected_transaction_id: str = "synthetic-ui-review-001"): 
    workspace = workspace.resolve()
    if not workspace.exists():
        prepare_demo(workspace)
    if not workspace.is_dir() or workspace.is_symlink():
        raise RuntimeError("Local demo workspace must be a real directory")
    private_file = workspace / "private_config.json"
    if private_file.is_symlink() or not private_file.is_file():
        raise RuntimeError("Missing safe private demo config; create a new workspace")
    if os.name != "nt" and private_file.stat().st_mode & 0o077:
        raise RuntimeError("Private demo config is readable by group/others")
    config = json.loads(private_file.read_text(encoding="utf-8"))
    fields = {
        "GRAPHGUARD_DEMO_REVIEW_KEY",
        "GRAPHGUARD_DEMO_AUDIT_KEY",
        "GRAPHGUARD_LEDGER_PATH",
        "GRAPHGUARD_MODEL_DIR",
        "GRAPHGUARD_TRUSTED_MANIFEST_SHA256",
    }
    if set(config) != fields:
        raise RuntimeError("Private configuration schema mismatch")
    if not (ROOT / "frontend" / "node_modules" / "next").exists():
        raise RuntimeError("Install frontend dependencies first: npm --prefix frontend ci")
    _refresh_private_tokens(workspace, config["GRAPHGUARD_DEMO_REVIEW_KEY"])
    environment = os.environ.copy()
    private_environment = dict(environment)
    private_environment.update(config)
    public_environment = dict(environment)
    for key in fields:
        public_environment.pop(key, None)  # NEVER pass signing secrets to Next.
    if "NEXT_PUBLIC_" in " ".join(config):
        raise RuntimeError("Unexpected public signing configuration")
    processes = []
    try:
        # Both processes bind to LOOPBACK, never public interfaces.
        processes.append(subprocess.Popen(
            [sys.executable, "-m", "ml.review.serve_local"],
            cwd=ROOT, env=private_environment, start_new_session=(os.name != "nt"),
        ))
        processes.append(subprocess.Popen(
            ["npm", "--prefix", "frontend", "run", "dev", "--", "--hostname", "127.0.0.1"],
            cwd=ROOT, env=public_environment, start_new_session=(os.name != "nt"),
        ))
        print("Local synthetic analyst desk: http://127.0.0.1:3000/cases", flush=True)
        print("Private signed demo tokens: " + str(workspace / "reviewer_tokens.json"), flush=True)
        print("Sample accepted synthetic ID: synthetic-ui-review-002", flush=True)
        print("Local fixture bypasses Kafka; real Kafka→case verified in CI. Ctrl-C to stop.", flush=True)
        if smoke:
            _smoke_browser_proxy(workspace, processes)
            return
        if browser_smoke:
            if evidence_dir is None:
                raise RuntimeError("A private/synthetic evidence directory is required")
            from ml.review.browser_acceptance import run_browser_acceptance
            run_browser_acceptance(workspace, processes, evidence_dir=evidence_dir,
                                   expected_transaction_id=expected_transaction_id)
            return
        while all(proc.poll() is None for proc in processes):
            time.sleep(0.5)
        raise RuntimeError("One of the local review services exited early")
    except KeyboardInterrupt:
        return
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                if os.name != "nt":
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description="One-command signed GraphGuard synthetic local UI")
    parser.add_argument("--workspace", type=Path, default=Path(".local/graphguard-review"))
    parser.add_argument("--smoke", action="store_true",
                        help="Start both servers, assert local HTTP score/SHAP/review, then tear down")
    parser.add_argument("--browser-smoke", action="store_true",
                        help="Run actual Chromium signed synthetic case workflow and exit")
    parser.add_argument("--evidence-dir", type=Path,
                        help="Output synthetic-only evidence JSON and safe screenshot")
    args = parser.parse_args()
    if args.smoke and args.browser_smoke:
        parser.error("Choose one acceptance mode")
    run_local(args.workspace, smoke=args.smoke,
              browser_smoke=args.browser_smoke, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    main()
