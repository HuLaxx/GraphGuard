import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency: string = "USD"): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(amount);
}

export function formatNumber(value: number): string {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
}

export function formatPercent(value: number, decimals: number = 1): string {
    return `${(value * 100).toFixed(decimals)}%`;
}

export function formatDate(date: string | Date): string {
    return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(date));
}

export function getFraudScoreColor(score: number): string {
    if (score >= 0.8) return "text-red-400";
    if (score >= 0.6) return "text-amber-400";
    if (score >= 0.4) return "text-amber-300";
    return "text-emerald-400";
}

export function getFraudBgColor(score: number): string {
    if (score >= 0.8) return "bg-red-500/10 text-red-400";
    if (score >= 0.6) return "bg-amber-500/10 text-amber-400";
    if (score >= 0.4) return "bg-amber-500/10 text-amber-300";
    return "bg-emerald-500/10 text-emerald-400";
}

export function getPriorityColor(priority: string): string {
    const colors: Record<string, string> = {
        CRITICAL: "bg-red-600 text-white",
        HIGH: "bg-red-500 text-white",
        MEDIUM: "bg-amber-500 text-zinc-900",
        LOW: "bg-emerald-500 text-zinc-900",
    };
    return colors[priority] || "bg-zinc-600 text-white";
}

export function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
        PENDING: "bg-zinc-700 text-zinc-300",
        IN_REVIEW: "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20",
        RESOLVED_FRAUD: "bg-red-500/10 text-red-400 border border-red-500/20",
        RESOLVED_LEGITIMATE: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
        ESCALATED: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    };
    return colors[status] || "bg-zinc-700 text-zinc-400";
}
