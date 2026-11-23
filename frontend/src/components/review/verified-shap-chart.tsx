"use client";

import type { ReviewExplanation } from "@/lib/signed-review";

interface VerifiedShapChartProps {
    explanation: ReviewExplanation;
}

export function VerifiedShapChart({ explanation }: VerifiedShapChartProps) {
    const contributions = [...explanation.all_features]
        .sort((a, b) => Math.abs(b.shap_log_odds) - Math.abs(a.shap_log_odds));
    const maxAbs = Math.max(0.001, ...contributions.map((item) => Math.abs(item.shap_log_odds)));

    return (
        <section aria-label="Verified model attribution" className="rounded-3xl border border-white/10 bg-zinc-900/85 p-5 sm:p-7">
            <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="mb-2 text-xs font-semibold text-violet-300">Model interpretability</p>
                    <h2 className="text-xl font-semibold tracking-tight text-white">Verified feature attributions</h2>
                    <p className="mt-2 max-w-lg text-sm leading-relaxed text-zinc-400">
                        Native SHAP values for this exact trained model and transaction. Contributions are
                        measured in <strong className="font-medium text-zinc-200">log odds</strong>, not probability points.
                    </p>
                </div>
                <div className="rounded-2xl border border-violet-400/20 bg-violet-400/10 px-4 py-3 text-right">
                    <div className="text-xs text-violet-200">Synthetic model output</div>
                    <div className="mt-1 text-2xl font-semibold tabular-nums text-white">
                        {(explanation.verified_model_probability * 100).toFixed(1)}%
                    </div>
                    <p className="text-[11px] text-violet-200/70">Uncalibrated · not a fraud verdict</p>
                </div>
            </header>
            <figure>
                <figcaption className="mb-4 text-xs text-zinc-400">
                    Signed additive contributions · all {contributions.length} features · baseline{" "}
                    {explanation.base_log_odds.toFixed(3)} log odds
                </figcaption>
                <div className="space-y-3">
                    {contributions.map((item) => {
                        const positive = item.shap_log_odds > 0;
                        const width = Math.min(49.5, 49.5 * Math.abs(item.shap_log_odds) / maxAbs);
                        return (
                            <div key={item.feature} className="grid gap-2 sm:grid-cols-[170px_minmax(0,1fr)_72px] sm:items-center">
                                <span title={item.feature} className="truncate text-xs text-zinc-300">{item.feature.replace(/_/g, " ")}</span>
                                <div className="relative h-5 overflow-hidden rounded-md bg-zinc-800/60" aria-hidden="true">
                                    <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-400/50" />
                                    <div
                                        className={positive ? "absolute inset-y-0 rounded-sm bg-rose-400/80" : "absolute inset-y-0 rounded-sm bg-cyan-400/80"}
                                        style={{
                                            width: width + "%",
                                            left: positive ? "50%" : 50 - width + "%",
                                        }}
                                    />
                                </div>
                                <span className="text-right text-xs tabular-nums text-zinc-200" aria-label={item.feature + ": " + item.shap_log_odds.toFixed(4) + " log odds"}>
                                    {item.shap_log_odds > 0 ? "+" : ""}{item.shap_log_odds.toFixed(3)}
                                </span>
                            </div>
                        );
                    })}
                </div>
                <div className="mt-5 flex flex-wrap gap-5 text-xs text-zinc-400">
                    <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm bg-rose-400" /> Raises model log odds</span>
                    <span><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm bg-cyan-400" /> Lowers model log odds</span>
                </div>
            </figure>
            <div className="mt-6 space-y-2 rounded-2xl border border-white/10 bg-black/35 p-4 text-xs leading-relaxed text-zinc-300">
                <p><strong className="text-zinc-100">Method:</strong> {explanation.method.replace(/_/g, " ")}</p>
                <p><strong className="text-zinc-100">Reconstruction difference:</strong> {explanation.reconstruction_abs_error.toExponential(2)}</p>
                <p className="font-medium text-amber-300">{explanation.non_causal_notice}</p>
            </div>
        </section>
    );
}
