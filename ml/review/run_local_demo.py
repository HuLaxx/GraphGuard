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


def run_local(workspace: Path):
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
    args = parser.parse_args()
    run_local(args.workspace)


if __name__ == "__main__":
    main()
