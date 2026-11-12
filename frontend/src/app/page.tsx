"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
    Shield,
    Zap,
    Brain,
    Database,
    Layers,
    ArrowRight,
    Play,
    Sparkles,
    Globe,
    Network,
    AlertTriangle,
    CheckCircle,
    Activity,
    Code
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";

const features = [
    {
        icon: Network,
        title: "Graph Analytics",
        description: "Neo4j-backed network analysis with PageRank and community detection to surface suspicious rings.",
        color: "from-zinc-100 to-zinc-400",
        delay: 0,
    },
    {
        icon: Brain,
        title: "ML Training + Explainability",
        description: "XGBoost and GAT training scripts with MLflow logs and SHAP explanations surfaced in the UI.",
        color: "from-zinc-100 to-zinc-500",
        delay: 100,
    },
    {
        icon: Zap,
        title: "Streaming + Features",
        description: "Kafka + Flink CEP for real-time patterns and Spark/Feast for feature engineering (local stack).",
        color: "from-white to-zinc-400",
        delay: 200,
    },
    {
        icon: AlertTriangle,
        title: "RAG Assistant",
        description: "Local-first investigator copilot with Groq/Ollama options and pgvector-backed retrieval.",
        color: "from-zinc-200 to-zinc-500",
        delay: 300,
    },
    {
        icon: Database,
        title: "Feature Store",
        description: "Feast feature repo with Redis cache and Postgres + pgvector for retrieval data.",
        color: "from-zinc-300 to-zinc-600",
        delay: 400,
    },
    {
        icon: Layers,
        title: "Full-Stack",
        description: "Next.js 16 + FastAPI + GraphQL with Docker Compose for local runs and free-tier demo targets.",
        color: "from-white to-zinc-500",
        delay: 500,
    },
];

const stats = [
    { value: "32", label: "Tests (Local Run)", icon: CheckCircle },
    { value: "12", label: "Local Services", icon: Globe },
    { value: "2", label: "Model Families", icon: Brain },
    { value: "3", label: "Primary Stores", icon: Database },
];

function FeatureCard({ feature, index }: { feature: (typeof features)[0]; index: number }) {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="group relative p-6 bg-zinc-900/50 border border-zinc-800 rounded-2xl hover:border-zinc-700 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-zinc-500/10"
            style={{ animationDelay: `${feature.delay}ms` }}
        >
            <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

            <div className={`relative w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 transition-transform duration-300 ${isHovered ? "scale-110 rotate-3" : ""}`}>
                <feature.icon className="w-6 h-6 text-zinc-950" />
            </div>

            <h3 className="text-xl font-semibold text-zinc-100 mb-2 group-hover:text-zinc-300 transition-colors">
                {feature.title}
            </h3>
            <p className="text-zinc-400 text-sm leading-relaxed">
                {feature.description}
            </p>
        </div>
    );
}

export default function HomePage() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        const frame = requestAnimationFrame(() => setMounted(true));
        return () => cancelAnimationFrame(frame);
    }, []);

    return (
        <div className="min-h-screen bg-transparent overflow-x-hidden">
            <Header />

            {/* Hero Section */}
            <section className="relative pt-28 pb-20 overflow-hidden">
                {/* Animated Background */}
                <div className="absolute inset-0">
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-800/20 via-zinc-950 to-zinc-950" />
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-zinc-500/10 rounded-full blur-[150px] animate-pulse" />
                    <div className="absolute top-20 left-1/4 w-[400px] h-[400px] bg-zinc-400/5 rounded-full blur-[100px]" />
                    <div className="absolute top-40 right-1/4 w-[300px] h-[300px] bg-white/5 rounded-full blur-[100px]" />
                </div>

                {/* Grid pattern */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />

                <div className="relative max-w-7xl mx-auto px-6">
                    <div className={`text-center max-w-4xl mx-auto transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
                        {/* Badge */}
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zinc-900/80 border border-zinc-800 text-sm text-zinc-400 mb-8 backdrop-blur-sm">
                            <Sparkles className="w-4 h-4 text-zinc-100" />
                            Portfolio Build - Evidence-First - Local-First
                        </div>

                        {/* Title */}
                        <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
                            <span className="bg-gradient-to-r from-zinc-200 via-zinc-400 to-zinc-500 bg-clip-text text-transparent">
                                Real-Time Fraud
                            </span>
                            <br />
                            <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent animate-gradient-x">
                                Intelligence Platform
                            </span>
                        </h1>

                        {/* Subtitle */}
                        <p className="text-lg md:text-xl text-zinc-400 mb-10 max-w-2xl mx-auto leading-relaxed">
                            Portfolio-grade fraud detection platform with graph analytics,
                            ML training pipelines, and a local-first RAG assistant.
                        </p>

                        {/* CTAs */}
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link
                                href="/demo"
                                className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-zinc-100 to-zinc-400 text-zinc-950 rounded-xl font-semibold text-lg transition-all shadow-xl shadow-white/10 hover:shadow-white/20 hover:scale-[1.02]"
                            >
                                <Play className="w-5 h-5 transition-transform group-hover:scale-110" />
                                Launch Demo
                                <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                            </Link>
                            <Link
                                href="/architecture"
                                className="flex items-center gap-2 px-8 py-4 bg-zinc-900/80 border border-zinc-700 text-zinc-100 rounded-xl font-semibold text-lg hover:bg-zinc-800 hover:border-zinc-500 transition-all backdrop-blur-sm"
                            >
                                View Architecture
                            </Link>
                        </div>
                    </div>

                    {/* Stats */}
                    <div className={`grid grid-cols-2 md:grid-cols-4 gap-8 mt-20 transition-all duration-1000 delay-300 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
                        {stats.map((stat) => (
                            <div key={stat.label} className="text-center">
                                <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-center">
                                    <stat.icon className="w-5 h-5 text-zinc-100" />
                                </div>
                                <p className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
                                    {stat.value}
                                </p>
                                <p className="text-sm text-zinc-500 mt-1">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-24 relative">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-zinc-700/10 via-transparent to-transparent" />

                <div className="relative max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-800/30 border border-zinc-700/50 text-zinc-100 text-sm mb-4">
                            <CheckCircle className="w-4 h-4" />
                            Evidence-Based Features
                        </div>
                        <h2 className="text-3xl md:text-5xl font-bold text-zinc-100 mb-4">
                            Built for Proof, Not Hype
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto text-lg">
                            Every section maps to code in this repo. Heavy services
                            run locally; the hosted demo is intentionally lightweight.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((feature, index) => (
                            <FeatureCard key={feature.title} feature={feature} index={index} />
                        ))}
                    </div>
                </div>
            </section>

            {/* Operational Snapshot */}
            <section className="py-16 px-6">
                <div className="max-w-5xl mx-auto">
                    <div className="p-8 rounded-2xl border border-zinc-800 bg-zinc-900/50">
                        <div className="flex items-center gap-3 mb-6">
                            <Activity className="w-6 h-6 text-zinc-200" />
                            <h3 className="text-xl font-semibold text-zinc-100">Operational Snapshot</h3>
                            <span className="ml-auto px-3 py-1 rounded-full bg-zinc-800/80 text-zinc-300 text-xs font-medium">
                                Local Evidence
                            </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {[
                                "Kafka producer + consumer flow for transactions",
                                "Neo4j graph build and algorithms scripts",
                                "FastAPI scoring with Redis cache and metrics",
                                "GraphQL fraud queue powering the UI",
                                "Local RAG indexing and Q&A endpoints",
                                "Prometheus metrics wired to /metrics",
                            ].map((item) => (
                                <div
                                    key={item}
                                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-zinc-800/50 transition-colors"
                                >
                                    <CheckCircle className="w-4 h-4 text-zinc-300 flex-shrink-0" />
                                    <span className="text-sm text-zinc-400">{item}</span>
                                </div>
                            ))}
                        </div>

                        <p className="text-xs text-zinc-500 mt-4">
                            Each item maps to code in this repo. Heavy services run locally; hosted demos are intentionally lightweight.
                        </p>
                    </div>
                </div>
            </section>

            {/* Developer API Section */}
            <section className="py-20 relative overflow-hidden">
                <div className="relative max-w-6xl mx-auto px-6">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-6">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-800/40 border border-zinc-700 text-zinc-200 text-sm">
                                <Code className="w-4 h-4" />
                                Developer API
                            </div>
                            <h2 className="text-3xl md:text-5xl font-bold leading-tight text-zinc-100">
                                Fraud scoring and graph insights on demand.
                            </h2>
                            <p className="text-lg text-zinc-400 leading-relaxed">
                                The demo UI is backed by a FastAPI + GraphQL layer. Use REST for scoring and GraphQL for
                                the fraud queue, explanations, and network data.
                            </p>
                            <ul className="space-y-3 text-zinc-400 text-sm">
                                {[
                                    "REST scoring endpoint for transaction risk",
                                    "GraphQL fraud queue for analyst workflows",
                                    "SHAP explanations for model transparency",
                                ].map((item) => (
                                    <li key={item} className="flex items-start gap-3">
                                        <div className="w-5 h-5 rounded-full bg-zinc-800 flex items-center justify-center mt-0.5">
                                            <CheckCircle className="w-3 h-3 text-zinc-200" />
                                        </div>
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="relative group">
                            <div className="absolute -inset-1 bg-gradient-to-r from-zinc-600 to-zinc-300 rounded-xl blur opacity-20 group-hover:opacity-30 transition duration-1000" />
                            <div className="relative rounded-xl border border-zinc-800 bg-[#0D0E12] p-6 shadow-2xl">
                                <div className="flex items-center justify-between mb-4 border-b border-zinc-800 pb-4">
                                    <div className="flex gap-2">
                                        <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                                        <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                                        <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
                                    </div>
                                    <span className="text-xs text-zinc-500 font-mono">POST /score</span>
                                </div>

                                <pre className="font-mono text-xs sm:text-sm leading-relaxed overflow-x-auto text-zinc-200/90">
                                    <code>{`curl -X POST http://localhost:8000/score \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"transaction_id\": \"txn_123\",
    \"amount\": 740.25,
    \"merchant\": \"Retail\"
  }'`}</code>
                                </pre>

                                <div className="mt-4 pt-4 border-t border-zinc-800/50">
                                    <div className="text-xs text-zinc-500 mb-2">Response (200 OK)</div>
                                    <pre className="font-mono text-xs leading-relaxed text-zinc-200/90">
                                        <code>{`{
  \"fraud_score\": 0.87,
  \"decision\": \"review\"
}`}</code>
                                    </pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
