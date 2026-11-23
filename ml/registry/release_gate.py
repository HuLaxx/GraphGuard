"""Train the synthetic GraphGuard baseline, register it in MLflow and gate promotion.

Run:  python -m ml.registry.release_gate --workspace .local/registry
      python -m ml.registry.release_gate --workspace .local/registry --sabotage shuffled-train-labels --expect-reject

Every run is logged to a local MLflow tracking store (SQLite, no server, no cloud)
and the XGBoost model is registered as a new model version. The version gets the
alias "candidate". Only if every metric clears release_policy.json does it also
get "champion". A rejected candidate never moves "champion".

SYNTHETIC ONLY: the metrics measure this repo's seeded generator, not real fraud.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

POLICY_PATH = Path(__file__).with_name("release_policy.json")


def load_policy(path: Path = POLICY_PATH) -> dict:
    policy = json.loads(path.read_text())
    for key in ("registered_model_name", "model", "split", "minimums", "maximums"):
        if key not in policy:
            raise ValueError(f"release policy missing {key!r}")
    return policy


def evaluate_gate(metrics: dict, policy: dict) -> dict:
    """Pure check of one model/split's metrics against the policy. No MLflow here."""
    checks = []
    for name, floor in policy["minimums"].items():
        value = float(metrics[name])
        checks.append({"metric": name, "value": value, "rule": ">=", "limit": floor, "passed": value >= floor})
    for name, ceiling in policy["maximums"].items():
        value = float(metrics[name])
        checks.append({"metric": name, "value": value, "rule": "<=", "limit": ceiling, "passed": value <= ceiling})
    return {"passed": all(c["passed"] for c in checks), "checks": checks}


def shuffle_train_labels(splits: dict, seed: int) -> dict:
    """Deliberately break the training labels to prove the gate rejects a bad model."""
    labels = [row["synthetic_label"] for row in splits["train"]]
    random.Random(seed + 1).shuffle(labels)
    train = [dict(row, synthetic_label=label) for row, label in zip(splits["train"], labels)]
    return {**splits, "train": train}


def markdown(report: dict) -> str:
    verdict = "PROMOTED to champion" if report["gate"]["passed"] else "REJECTED (champion unchanged)"
    lines = [
        f"### Model release gate: {verdict}",
        "",
        f"Registered `{report['registered_model_name']}` version **{report['model_version']}** "
        f"(aliases: {', '.join(report['aliases'])}). Sabotage: `{report['sabotage']}`. Synthetic data only.",
        "",
        "| Metric | Value | Rule | Limit | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in report["gate"]["checks"]:
        lines.append(f"| {c['metric']} | {c['value']:.4f} | {c['rule']} | {c['limit']} | {'pass' if c['passed'] else 'FAIL'} |")
    lines.append("")
    lines.append(f"Champion version after this run: {report['champion_version_after']}")
    return "\n".join(lines) + "\n"


def run(workspace: Path, *, count: int, seed: int, sabotage: str | None) -> dict:
    import mlflow
    import mlflow.xgboost
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient

    from ml.training.pit_baselines import (
        chronological_split, export_artifacts, fit_baselines, make_synthetic_dataset,
    )

    policy = load_policy()
    workspace.mkdir(parents=True, exist_ok=True)
    tracking_uri = f"sqlite:///{(workspace / 'mlflow.db').resolve()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)
    experiment = "graphguard-synthetic-release"
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=(workspace / "artifacts").resolve().as_uri())
    mlflow.set_experiment(experiment)
    client = MlflowClient()
    name = policy["registered_model_name"]

    def champion_version():
        try:
            return client.get_model_version_by_alias(name, "champion").version
        except MlflowException:
            return None

    champion_before = champion_version()
    rows = make_synthetic_dataset(count=count, seed=seed)
    splits = chronological_split(rows)
    if sabotage == "shuffled-train-labels":
        splits = shuffle_train_labels(splits, seed)
    elif sabotage is not None:
        raise ValueError(f"unknown sabotage {sabotage!r}")
    trained = fit_baselines(splits, seed=seed)
    artifacts_dir = workspace / "run-artifacts"
    manifest = export_artifacts(rows, trained, artifacts_dir, seed=seed)
    # export_artifacts records the evaluation of the models it was given, which
    # for a sabotaged run is the broken model.
    metrics = trained["results"][policy["model"]][policy["split"]]
    gate = evaluate_gate(metrics, policy)

    with mlflow.start_run(run_name=f"seed{seed}-{sabotage or 'clean'}") as active:
        mlflow.set_tags({
            "scope": "synthetic-only", "sabotage": sabotage or "none",
            "gate": "passed" if gate["passed"] else "rejected",
        })
        mlflow.log_params({
            "seed": seed, "rows": count, "model": policy["model"],
            "dataset_sha256": manifest["dataset_sha256"],
            "feature_version": manifest["feature_version"],
            "generator_version": manifest["generator_version"],
        })
        for model_name, splits_metrics in trained["results"].items():
            for split_name, values in splits_metrics.items():
                mlflow.log_metrics({
                    f"{model_name}.{split_name}.{k}": float(v)
                    for k, v in values.items() if isinstance(v, (int, float))
                })
        mlflow.log_artifact(str(artifacts_dir / "manifest.json"))
        mlflow.xgboost.log_model(trained["models"]["xgboost"], artifact_path="model")
        run_id = active.info.run_id

    version = mlflow.register_model(f"runs:/{run_id}/model", name).version
    client.set_model_version_tag(name, version, "gate", "passed" if gate["passed"] else "rejected")
    client.set_registered_model_alias(name, "candidate", version)
    aliases = ["candidate"]
    if gate["passed"]:
        client.set_registered_model_alias(name, "champion", version)
        aliases.append("champion")

    # A trusted reload of the registered champion must reproduce its test predictions.
    champion_after = champion_version()
    if champion_after is not None and gate["passed"]:
        import numpy as np
        from ml.training.pit_baselines import to_xy
        reloaded = mlflow.xgboost.load_model(f"models:/{name}@champion")
        x_test, _ = to_xy(splits["test"])
        if not np.allclose(
            reloaded.predict_proba(x_test), trained["models"]["xgboost"].predict_proba(x_test),
            atol=1e-8, rtol=1e-8,
        ):
            raise RuntimeError("Registered champion did not reproduce its test predictions")

    return {
        "registered_model_name": name,
        "model_version": str(version),
        "run_id": run_id,
        "sabotage": sabotage or "none",
        "aliases": aliases,
        "gate": gate,
        "champion_version_before": champion_before,
        "champion_version_after": champion_after,
        "tracking_uri": tracking_uri,
        "scope": manifest["scope"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", type=Path, default=Path(".local/registry"))
    parser.add_argument("--count", type=int, default=720)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sabotage", choices=["shuffled-train-labels"], default=None)
    parser.add_argument("--expect-reject", action="store_true",
                        help="exit 0 only if the gate rejects the candidate and champion is unchanged")
    args = parser.parse_args(argv)
    report = run(args.workspace, count=args.count, seed=args.seed, sabotage=args.sabotage)
    (args.workspace / f"gate_report_{report['sabotage']}.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    text = markdown(report)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    if args.expect_reject:
        ok = (not report["gate"]["passed"]) and report["champion_version_after"] == report["champion_version_before"]
        return 0 if ok else 1
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
