"""Reproducible LOCAL synthetic signed-review latency microbenchmark.

This is a small controlled loopback benchmark, NOT an online production
SLO, high-scale stress test, cloud performance result or fraud decision.
Never stores bearer tokens in reports or logs.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
import time
from urllib import request as http_request

SCOPE = "LOCAL_SYNTHETIC_BENCHMARK_NOT_PRODUCTION"
BASE_URL = "http://127.0.0.1:3000/review-local/"


def summarize_latencies(times_ms: list[float]) -> dict:
    if not times_ms or not all(isinstance(x, (float, int)) and x >= 0 for x in times_ms):
        raise ValueError("Nonempty finite nonnegative measured durations required")
    from math import isfinite
    if not all(isfinite(x) for x in times_ms):
        raise ValueError("Nonfinite measured durations")
    values = sorted(float(x) for x in times_ms)
    n = len(values)
    # Explicit nearest-rank percentile, robust with low sample counts.
    return {
        "count": n,
        "min_ms": round(values[0], 3),
        "p50_ms": round(values[ceil(n * 0.50) - 1], 3),
        "p95_ms": round(values[ceil(n * 0.95) - 1], 3),
        "max_ms": round(values[-1], 3),
    }


def _get(path: str, token: str) -> dict:
    req = http_request.Request(
        BASE_URL + path,
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    with http_request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("Local review request returned non-200")
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RuntimeError("Non-object local API response")
    return payload


def run_benchmark(
    workspace: Path, processes: list,
    *, evidence_dir: Path, concurrency: int = 2, calls_per_route: int = 12,
) -> dict:
    if not 1 <= concurrency <= 4 or not 6 <= calls_per_route <= 40:
        raise ValueError("Out-of-bounds bounded local test workload")
    workspace = Path(workspace).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    if evidence_dir.is_symlink() or workspace.is_symlink():
        raise RuntimeError("Refusing symlink local benchmark artifacts")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    token_file = workspace / "reviewer_tokens.json"
    if token_file.is_symlink():
        raise RuntimeError("Refusing symlink bearer token file")
    token = json.loads(token_file.read_text(encoding="utf-8"))["analyst"]
    # A single warm call exercises Next dev compilation and signed route
    # authorization; cold startup is intentionally excluded from samples.
    deadline = time.monotonic() + 160
    while True:
        if any(proc.poll() is not None for proc in processes):
            raise RuntimeError("Local API or frontend stopped before benchmark")
        try:
            who = _get("session", token)
            if who["scope"] != "SYNTHETIC_LOCAL_REVIEW_ONLY":
                raise RuntimeError("Untrusted benchmark API scope")
            data = _get("cases", token)
            if len(data["cases"]) != 1:
                raise RuntimeError("Expected one accepted synthetic review case")
            case = data["cases"][0]
            break
        except Exception as error:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Local signed review startup failed: " + type(error).__name__
                ) from None
            time.sleep(1)
    cid = case["case_id"]
    expected = case["evidence"]
    # Exercise real SHAP API once before measuring to exclude first-use
    # compilation, but NOT model inference or hash checks in measured calls.
    first_explanation = _get("cases/" + cid + "/explanation", token)
    if (
        first_explanation["explanation_sha256"] != expected["explanation_sha256"]
        or first_explanation["model_sha256"] != expected["model_sha256"]
    ):
        raise RuntimeError("Warm SHAP differs from original signed evidence")

    routes = (
        [("case_read", "cases/" + cid)] * calls_per_route +
        [("native_shap", "cases/" + cid + "/explanation")] * calls_per_route
    )

    def measure(item):
        label, path = item
        start = time.perf_counter_ns()
        try:
            payload = _get(path, token)
            if label == "case_read":
                if payload["evidence"] != expected or payload["status"] != "OPEN":
                    raise RuntimeError("Case evidence changed during read test")
            else:
                if (
                    payload["explanation_sha256"] != expected["explanation_sha256"]
                    or payload["model_sha256"] != expected["model_sha256"]
                    or payload["verified_model_probability"] != expected["score"]
                    or len(payload["all_features"]) != 12
                ):
                    raise RuntimeError("Native SHAP/source/model did not match")
            error = None
        except Exception as exc:
            error = type(exc).__name__   # Never log token, response or PII.
        duration = (time.perf_counter_ns() - start) / 1_000_000
        return label, duration, error

    with ThreadPoolExecutor(max_workers=concurrency) as workers:
        measures = list(workers.map(measure, routes))
    per_route = {}
    failures = []
    for label in ("case_read", "native_shap"):
        entries = [(d, err) for key, d, err in measures if key == label]
        good = [d for d, err in entries if err is None]
        errors = [err for _, err in entries if err is not None]
        failures.extend(errors)
        per_route[label] = {
            "completed": len(good),
            "failed": len(errors),
            "error_types": sorted(set(errors)),
            "timing": summarize_latencies(good) if good else None,
        }
    report = {
        "scope": SCOPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "urllib_loopback_signed_Next_proxy_to_FastAPI",
        "model_source": "deterministic_synthetic_direct_SQLite_seed",
        "warm_up": "excluded_Next_startup_and_first_SHAP_call",
        "concurrency": concurrency,
        "planned_calls": len(routes),
        "successful_calls": len(routes) - len(failures),
        "failed_calls": len(failures),
        "routes": per_route,
        "case_source_sha256": expected["source_payload_sha256"],
        "model_sha256": expected["model_sha256"],
        "explanation_sha256": expected["explanation_sha256"],
        "note": "Descriptive CI sample only. No p95 SLO, cloud bill, real data, or production capacity claim.",
    }
    (evidence_dir / "synthetic-latency.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        raise AssertionError("Some local signed synthetic requests failed; report retained")
    print(
        f"PASS: {len(routes)} signed local requests across {concurrency} "
        "workers, 0 failures. See synthetic-latency.json for measured p50/p95.",
        flush=True,
    )
    return report
