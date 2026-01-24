"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@apollo/client";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { MetricsGrid, FraudQueue, NetworkGraph, ShapChart } from "@/components/dashboard";
import { RagAssistant } from "@/components/assistant/rag-assistant";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatDate, formatPercent } from "@/lib/utils";
import { CheckCircle, XCircle, RefreshCw } from "lucide-react";
import type { FraudCase, GraphNode, GraphLink } from "@/types";
import { GET_DASHBOARD_DATA, GET_SUSPICIOUS_SUBGRAPH, GET_SHAP_EXPLANATION, LABEL_CASE_MUTATION } from "@/lib/queries";

export default function DemoPage() {
    const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

    // 1. Fetch Dashboard Data
    const { data: dashData, loading: dashLoading, error: dashError, refetch: dashRefetch } = useQuery(GET_DASHBOARD_DATA, {
        pollInterval: 5000,
    });

    // Determine Active Case
    const activeCase = dashData?.fraudQueue?.items?.find((c: any) => c.id === selectedCaseId) || dashData?.fraudQueue?.items?.[0];
    const activeUserId = activeCase?.userId;
    const activeTxnId = activeCase?.transactionId;

    // 2. Fetch Subgraph
    const { data: graphData } = useQuery(GET_SUSPICIOUS_SUBGRAPH, {
        variables: { userId: activeUserId || "unknown", hops: 2 },
        skip: !activeUserId,
    });

    // 3. Fetch SHAP Explanation
    const { data: shapData } = useQuery(GET_SHAP_EXPLANATION, {
        variables: { transactionId: activeTxnId || "unknown" },
        skip: !activeTxnId,
    });

    // 4. Mutations
    const [labelCase, { loading: labelLoading }] = useMutation(LABEL_CASE_MUTATION, {
        refetchQueries: [GET_DASHBOARD_DATA],
    });

    const handleLabel = async (label: string) => {
        if (!activeCase) return;
        try {
            await labelCase({
                variables: {
                    id: activeCase.id,
                    label,
                    notes: `Manually labeled as ${label}`
                }
            });
        } catch (e) {
            console.error("Mutation failed", e);
        }
    };

    // Handlers
    const handleCaseSelect = (c: FraudCase) => {
        setSelectedCaseId(c.id);
    };

    // Transform API data to UI types
    const metrics = dashData?.dashboardMetrics
        ? {
            totalTransactions: dashData.dashboardMetrics.totalTransactions ?? 0,
            fraudRate: dashData.dashboardMetrics.fraudRate ?? 0,
            pendingReview: dashData.dashboardMetrics.pendingReview ?? 0,
            autoApproved: dashData.dashboardMetrics.autoApproved ?? 0,
            autoDeclined: dashData.dashboardMetrics.autoDeclined ?? 0,
            p99LatencyMs: dashData.dashboardMetrics.p99LatencyMs ?? 0,
            modelAccuracy: dashData.dashboardMetrics.modelAccuracy ?? 0,
        }
        : {
            totalTransactions: 0,
            fraudRate: 0,
            pendingReview: 0,
            autoApproved: 0,
            autoDeclined: 0,
            p99LatencyMs: 0,
            modelAccuracy: 0,
        };

    const cases: FraudCase[] = (dashData?.fraudQueue?.items || []).map((item: any) => ({
        id: item.id,
        transactionId: item.transactionId,
        userId: item.userId,
        amount: item.amountVal,
        fraudScore: item.fraudScore,
        priority: item.priority,
        status: item.status,
        createdAt: item.createdAt,
        currency: item.currencyCode,
        merchantName: item.merchantName,
    }));

    const nodes: GraphNode[] = (graphData?.suspiciousSubgraph?.nodes || []).map((n: any) => ({
        id: n.id,
        type: n.type,
        label: n.label,
        riskScore: n.riskScore,
        fraud: n.isFlagged,
        pagerank: n.riskScore * 0.1,
    }));

    const links: GraphLink[] = (graphData?.suspiciousSubgraph?.edges || []).map((e: any) => ({
        source: e.source,
        target: e.target,
        amount: e.amount || 0,
        type: e.type,
    }));

    // Real SHAP Features
    const shapFeatures = shapData?.shapExplanation?.features || [];
    const shapPlainEnglish = shapData?.shapExplanation?.plainEnglish || "Loading explanation...";

    if (dashError) {
        return (
            <div className="min-h-screen bg-zinc-950 text-zinc-100">
                <Header />
                <main className="max-w-3xl mx-auto px-6 pt-28">
                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 space-y-3">
                        <h1 className="text-xl font-semibold">API not reachable</h1>
                        <p className="text-zinc-400">
                            The demo expects the GraphQL API at <span className="text-zinc-200">/graphql</span>.
                            Start the local API and refresh this page. If you are using a non-default port,
                            set <span className="text-zinc-200">NEXT_PUBLIC_API_PORT</span> (or
                            <span className="text-zinc-200">API_PORT</span>) before running the frontend.
                        </p>
                        <div className="rounded-xl bg-zinc-950 border border-zinc-800 p-4 text-sm text-zinc-300 font-mono">
                            python -m uvicorn ml.serving.api:app --reload --port 8000
                        </div>
                        <p className="text-zinc-500 text-sm">
                            Error detail: {dashError.message}
                        </p>
                    </div>
                </main>
                <Footer />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-zinc-950">
            <Header />

            <main className="max-w-7xl mx-auto px-6 pb-20 pt-28 space-y-8">
                {/* Page Header */}
                <section className="space-y-3 flex items-end justify-between">
                    <div>
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400 mb-4">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                            </span>
                            Demo Mode (Local-First)
                        </div>
                        <h1 className="text-4xl font-bold text-zinc-100">Fraud Operations Dashboard</h1>
                        <p className="text-zinc-400 max-w-2xl">
                            Demo UI wired to the GraphQL API. Hosted demos run on free-tier services with limited features.
                            For the full pipeline, run the local stack.
                        </p>
                    </div>
                    <Button variant="outline" size="icon" onClick={() => dashRefetch()} disabled={dashLoading}>
                        <RefreshCw className={`h-4 w-4 ${dashLoading ? 'animate-spin' : ''}`} />
                    </Button>
                </section>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-400">
                    Hosted demo targets use free-tier services (Supabase/Upstash/Railway). Heavy services like Kafka,
                    Neo4j, and Flink are local-only. For the full pipeline, run the Docker Compose stack locally.
                </div>

                <MetricsGrid metrics={metrics} />

                <div className="grid gap-4 md:grid-cols-3">
                    {[
                        {
                            title: 'Fraud queue',
                            desc: 'Live case list pulled from GraphQL with priority and status.',
                        },
                        {
                            title: 'Network view',
                            desc: 'D3-based graph from suspicious subgraph queries.',
                        },
                        {
                            title: 'Explainability',
                            desc: 'SHAP features with a plain-English summary.',
                        },
                    ].map((item) => (
                        <Card key={item.title} className="bg-zinc-900/60 border-zinc-800">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-zinc-200">{item.title}</CardTitle>
                            </CardHeader>
                            <CardContent className="text-sm text-zinc-500">
                                {item.desc}
                            </CardContent>
                        </Card>
                    ))}
                </div>

                <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                    <FraudQueue
                        cases={cases}
                        selectedId={activeCase?.id}
                        onSelect={handleCaseSelect}
                    />

                    <div className="space-y-4">
                        {activeCase ? (
                            <Card>
                                <CardHeader className="pb-2">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <CardTitle className="text-lg">Case Focus</CardTitle>
                                            <p className="text-sm text-zinc-500 mt-1">
                                                {activeCase.transactionId}
                                            </p>
                                        </div>
                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                                                onClick={() => handleLabel("LEGITIMATE")}
                                                disabled={labelLoading}
                                            >
                                                <CheckCircle className="h-4 w-4 mr-1" />
                                                Clear
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="destructive"
                                                onClick={() => handleLabel("FRAUD")}
                                                disabled={labelLoading}
                                            >
                                                <XCircle className="h-4 w-4 mr-1" />
                                                Confirm Fraud
                                            </Button>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-3 text-sm">
                                        <div>
                                            <p className="text-xs uppercase tracking-widest text-zinc-500">Risk score</p>
                                            <p className="font-semibold text-zinc-100">{formatPercent(activeCase.fraudScore, 0)}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-widest text-zinc-500">Status</p>
                                            <p className="font-semibold text-zinc-100">{activeCase.status?.replace("_", " ") || "UNKNOWN"}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-widest text-zinc-500">Amount</p>
                                            <p className="font-semibold text-zinc-100">{formatCurrency(activeCase.amount)}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-widest text-zinc-500">Detected</p>
                                            <p className="font-semibold text-zinc-100">{formatDate(activeCase.createdAt)}</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card>
                                <CardContent className="p-8 text-center text-zinc-500">
                                    Select a case to view details
                                </CardContent>
                            </Card>
                        )}

                        <ShapChart
                            features={shapFeatures}
                            predictionValue={activeCase?.fraudScore || 0}
                            plainEnglish={shapPlainEnglish}
                        />
                    </div>
                </div>

                <NetworkGraph
                    nodes={nodes}
                    links={links}
                    width={800}
                    height={400}
                    onNodeClick={(node) => console.log("Node clicked:", node)}
                />

                <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                    <RagAssistant />
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg">RAG Tips</CardTitle>
                        </CardHeader>
                        <CardContent className="text-sm text-zinc-400 space-y-2">
                            <p>Ask about data flow, model training, or infra setup.</p>
                            <p>Examples:</p>
                            <ul className="list-disc list-inside space-y-1 text-zinc-500">
                                <li>How do transactions reach Neo4j?</li>
                                <li>What features are used for XGBoost?</li>
                                <li>Where is drift detection implemented?</li>
                                <li>How does the RAG index get built?</li>
                            </ul>
                        </CardContent>
                    </Card>
                </div>
            </main>

            <Footer />
        </div>
    );
}
