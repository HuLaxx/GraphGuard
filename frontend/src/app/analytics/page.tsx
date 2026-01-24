"use client";

import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { MetricsGrid, ShapChart } from "@/components/dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatPercent } from "@/lib/utils";
import type { ShapFeature } from "@/types";

const mockMetrics = {
    totalTransactions: 125847,
    fraudRate: 0.023,
    casesPending: 342,
    casesResolved: 118234,
    avgLatencyMs: 45,
    modelAccuracy: 0.967,
};

const modelSignals = [
    { label: "Precision", value: 0.91, tone: "emerald" },
    { label: "Recall", value: 0.84, tone: "amber" },
    { label: "AUC-PR", value: 0.93, tone: "cyan" },
    { label: "Drift score", value: 0.04, tone: "emerald" },
];

const mockShapFeatures: ShapFeature[] = [
    { name: "txn_count_1h", value: 9, shapValue: 0.31, importance: 0.32, impact: "INCREASES" },
    { name: "amount_zscore", value: 2.6, shapValue: 0.24, importance: 0.25, impact: "INCREASES" },
    { name: "merchant_fraud_rate", value: 0.11, shapValue: 0.18, importance: 0.2, impact: "INCREASES" },
    { name: "device_age_days", value: 0.8, shapValue: 0.12, importance: 0.15, impact: "INCREASES" },
    { name: "pagerank", value: 0.02, shapValue: 0.08, importance: 0.1, impact: "INCREASES" },
    { name: "user_avg_amount", value: 120, shapValue: -0.05, importance: 0.06, impact: "DECREASES" },
];

const toneMap: Record<string, string> = {
    emerald: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    cyan: "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20",
};

export default function AnalyticsPage() {
    return (
        <div className="min-h-screen bg-zinc-950">
            <Header />

            <main className="max-w-7xl mx-auto px-6 pb-16 pt-28 space-y-8">
                <section className="space-y-3">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zinc-900/80 border border-zinc-800 text-sm text-zinc-400">
                        Model Analytics
                    </div>
                    <h1 className="text-4xl font-bold text-zinc-100">Performance and drift insights</h1>
                    <p className="text-zinc-400 max-w-2xl">
                        Track model behavior, drift signals, and explanation trends to keep fraud detection reliable.
                    </p>
                </section>

                <MetricsGrid metrics={mockMetrics} />

                <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg">Model health summary</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-3">
                                {modelSignals.map((signal) => (
                                    <div key={signal.label} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-3">
                                        <p className="text-xs uppercase tracking-widest text-zinc-500">{signal.label}</p>
                                        <div className="flex items-center justify-between mt-2">
                                            <p className="text-2xl font-bold text-zinc-100">
                                                {formatPercent(signal.value, 0)}
                                            </p>
                                            <span className={cn("text-xs font-semibold px-2 py-1 rounded-full", toneMap[signal.tone])}>
                                                stable
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="text-sm text-zinc-400">
                                Most drift is driven by new device fingerprints in North America. Monitor shared device
                                clusters before the next retraining run.
                            </div>
                        </CardContent>
                    </Card>

                    <ShapChart
                        features={mockShapFeatures}
                        predictionValue={0.78}
                        plainEnglish="Top drivers include transaction velocity, z-score deviation, and merchant risk."
                    />
                </div>
            </main>

            <Footer />
        </div>
    );
}

