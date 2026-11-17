import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { VerifiedShapChart } from "./verified-shap-chart";
import type { ReviewExplanation } from "@/lib/signed-review";

const fixture: ReviewExplanation = {
    transaction_id: "synthetic-fixture",
    scope: "SYNTHETIC_ONLY_RESEARCH_EXPLANATION",
    status: "RESEARCH_SCORE_ONLY_NO_AUTOMATED_DECISION",
    non_causal_notice: "Associations in a synthetic model; not causal evidence or proof of fraud.",
    method: "xgboost_native_exact_tree_shap_path_dependent",
    background: "tree_path_dependent_native_booster",
    attribution_scale: "raw_log_odds",
    reconstructed_probability: 0.64,
    verified_model_probability: 0.64,
    reconstruction_abs_error: 0.0,
    base_log_odds: 0.0,
    reconstructed_log_odds: 0.575,
    all_features: [
        { feature: "user_txn_count_24h", value: 4, shap_log_odds: 0.75, direction: "raises_model_log_odds" },
        { feature: "device_other_users_7d", value: 2, shap_log_odds: -0.175, direction: "lowers_model_log_odds" },
    ],
    top_features: [],
    model_sha256: "a".repeat(64),
    manifest_sha256: "b".repeat(64),
    source_payload_sha256: "c".repeat(64),
    feature_snapshot_sha256: "d".repeat(64),
    explanation_sha256: "e".repeat(64),
};

describe("actual model-derived synthetic SHAP chart", () => {
    it("renders signed log-odds attributions and non-causal notice", () => {
        const html = renderToStaticMarkup(createElement(VerifiedShapChart, { explanation: fixture }));
        expect(html).toContain("Verified feature attributions");
        expect(html).toContain("user txn count 24h");
        expect(html).toContain("device other users 7d");
        expect(html).toContain("+0.750");
        expect(html).toContain("-0.175");
        expect(html).toContain("log odds");
        expect(html).toContain("not causal evidence");
        expect(html).toContain("64.0%");
        expect(html).toContain("Uncalibrated");
    });
});
