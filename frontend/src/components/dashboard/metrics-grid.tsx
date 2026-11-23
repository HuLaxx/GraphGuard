"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LucideIcon, Activity, AlertTriangle, CheckCircle2, XCircle, Clock, Zap } from "lucide-react";

interface MetricCardProps {
    title: string;
    value: string | number;
    icon: LucideIcon;
    color: "blue" | "red" | "amber" | "green" | "purple" | "cyan";
    trend?: { value: string; isPositive: boolean };
}

const colorMap = {
    blue: { gradient: "from-zinc-100 to-zinc-400", text: "text-zinc-600" },
    red: { gradient: "from-zinc-200 to-zinc-500", text: "text-zinc-700" }, // Keep trend text semantic, but icon monochrome
    amber: { gradient: "from-zinc-100 to-zinc-300", text: "text-zinc-500" },
    green: { gradient: "from-white to-zinc-400", text: "text-zinc-600" },
    purple: { gradient: "from-zinc-300 to-zinc-600", text: "text-zinc-700" },
    cyan: { gradient: "from-zinc-100 to-zinc-500", text: "text-zinc-600" },
};

export function MetricCard({ title, value, icon: Icon, color, trend }: MetricCardProps) {
    return (
        <Card className="group hover:-translate-y-1 hover:shadow-xl hover:shadow-emerald-500/5">
            <CardContent className="p-5">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-xs uppercase tracking-widest text-zinc-500 mb-1">{title}</p>
                        <p className="text-2xl font-bold text-zinc-100">{value}</p>
                        {trend && (
                            <p className={cn("text-xs mt-1", trend.isPositive ? "text-emerald-400" : "text-red-400")}>
                                {trend.isPositive ? "↑" : "↓"} {trend.value}
                            </p>
                        )}
                    </div>
                    <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br", colorMap[color].gradient)}>
                        <Icon className="h-6 w-6 text-zinc-900" />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

interface MetricsGridProps {
    /** A previous server or parent-supplied snapshot; never infer a historical change. */
    previousMetrics?: MetricsGridProps["metrics"];
    metrics: {
        totalTransactions: number;
        fraudRate: number;
        pendingReview: number;
        autoApproved: number;
        autoDeclined: number;
        p99LatencyMs: number;
        modelAccuracy: number;
    };
}

function formatNumber(value: number): string {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
}

function formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
}

export function MetricsGrid({ metrics, previousMetrics }: MetricsGridProps) {
    const safeMetrics = {
        totalTransactions: metrics.totalTransactions ?? 0,
        fraudRate: metrics.fraudRate ?? 0,
        pendingReview: metrics.pendingReview ?? 0,
        autoApproved: metrics.autoApproved ?? 0,
        autoDeclined: metrics.autoDeclined ?? 0,
        p99LatencyMs: metrics.p99LatencyMs ?? 0,
        modelAccuracy: metrics.modelAccuracy ?? 0,
    };

    const prevMetrics = previousMetrics ?? null;
    const autoDecisions = safeMetrics.autoApproved + safeMetrics.autoDeclined;
    const prevAutoDecisions = prevMetrics
        ? prevMetrics.autoApproved + prevMetrics.autoDeclined
        : 0;

    const transactionDelta = prevMetrics
        ? safeMetrics.totalTransactions - prevMetrics.totalTransactions
        : null;
    const fraudRateDelta = prevMetrics
        ? safeMetrics.fraudRate - prevMetrics.fraudRate
        : null;
    const autoDecisionDelta = prevMetrics
        ? autoDecisions - prevAutoDecisions
        : null;

    const cards = [
        {
            title: "Transactions",
            value: formatNumber(safeMetrics.totalTransactions),
            icon: Activity,
            color: "cyan" as const,
            trend: transactionDelta === null
                ? undefined
                : {
                    value: `${formatNumber(Math.abs(transactionDelta))} since last refresh`,
                    isPositive: transactionDelta >= 0,
                },
        },
        {
            title: "Fraud Rate",
            value: formatPercent(safeMetrics.fraudRate),
            icon: AlertTriangle,
            color: "red" as const,
            trend: fraudRateDelta === null
                ? undefined
                : {
                    value: `${(Math.abs(fraudRateDelta) * 100).toFixed(2)}% since last refresh`,
                    isPositive: fraudRateDelta >= 0,
                },
        },
        {
            title: "Pending Review",
            value: safeMetrics.pendingReview.toString(),
            icon: Clock,
            color: "amber" as const,
        },
        {
            title: "Auto Decisions",
            value: autoDecisions.toString(),
            icon: CheckCircle2,
            color: "green" as const,
            trend: autoDecisionDelta === null
                ? undefined
                : {
                    value: `${Math.abs(autoDecisionDelta)} since last refresh`,
                    isPositive: autoDecisionDelta >= 0,
                },
        },
        {
            title: "Latency p99",
            value: `${safeMetrics.p99LatencyMs}ms`,
            icon: Zap,
            color: "purple" as const,
        },
        {
            title: "Model Accuracy",
            value: formatPercent(safeMetrics.modelAccuracy),
            icon: XCircle,
            color: "blue" as const,
        },
    ];

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {cards.map((card) => (
                <MetricCard key={card.title} {...card} />
            ))}
        </div>
    );
}
