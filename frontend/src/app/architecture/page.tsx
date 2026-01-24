'use client';

import {
    Database,
    Server,
    Monitor,
    Cpu,
    Cloud,
    ArrowRight,
    ArrowDown,
    Brain
} from 'lucide-react';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import Link from 'next/link';

const getLogoUrl = (name: string) => {
    const slugMap: Record<string, string> = {
        'Next.js': 'nextdotjs',
        'React 18': 'react',
        'D3.js': 'd3dotjs',
        'Tailwind': 'tailwindcss',
        'FastAPI': 'fastapi',
        'GraphQL': 'graphql',
        'Redis': 'redis',
        'Kafka': 'apachekafka',
        'Flink': 'apacheflink',
        'Feast': 'python',
        'XGBoost': 'python',
        'SHAP': 'python',
        'PyTorch': 'pytorch',
        'MLflow': 'mlflow',
        'PostgreSQL': 'postgresql',
        'Neo4j': 'neo4j',
        'pgvector': 'postgresql',
        'Docker Compose': 'docker',
        'Prometheus': 'prometheus',
        'Grafana': 'grafana',
    };
    const slug = slugMap[name] || name.toLowerCase().replace(/[^a-z0-9]/g, '');
    return `https://cdn.simpleicons.org/${slug}/white`;
};

const layers = [
    {
        name: 'Presentation Layer',
        icon: Monitor,
        color: 'from-zinc-100 to-zinc-400',
        bgColor: 'bg-zinc-100/10',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'Next.js', full: 'Next.js 16 App Router' },
            { name: 'React 18', full: 'React 18 with hooks' },
            { name: 'D3.js', full: 'Network visualization' },
            { name: 'Tailwind', full: 'Utility-first CSS' },
        ],
    },
    {
        name: 'API Layer',
        icon: Server,
        color: 'from-zinc-200 to-zinc-500',
        bgColor: 'bg-zinc-200/10',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'FastAPI', full: 'High-performance Python API' },
            { name: 'GraphQL', full: 'Strawberry schema + resolvers' },
            { name: 'Redis', full: 'Response caching & sessions' },
        ],
    },
    {
        name: 'Streaming Layer',
        icon: Cpu,
        color: 'from-white to-zinc-400',
        bgColor: 'bg-white/5',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'Kafka', full: 'Event streaming platform' },
            { name: 'Flink', full: 'CEP fraud patterns' },
            { name: 'Feast', full: 'Online feature serving' },
        ],
    },
    {
        name: 'ML Layer',
        icon: Brain,
        color: 'from-zinc-300 to-zinc-600',
        bgColor: 'bg-zinc-300/10',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'XGBoost', full: 'Gradient boosting ensemble' },
            { name: 'PyTorch', full: 'Graph Attention Networks' },
            { name: 'SHAP', full: 'Explainable AI' },
            { name: 'MLflow', full: 'Experiment tracking' },
        ],
    },
    {
        name: 'Data Layer',
        icon: Database,
        color: 'from-zinc-400 to-zinc-700',
        bgColor: 'bg-zinc-400/10',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'PostgreSQL', full: 'Transactional data' },
            { name: 'Neo4j', full: 'Graph database' },
            { name: 'Redis', full: 'Feature cache' },
            { name: 'pgvector', full: 'Vector search (Postgres extension)' },
        ],
    },
    {
        name: 'Infrastructure',
        icon: Cloud,
        color: 'from-zinc-100 to-zinc-300',
        bgColor: 'bg-zinc-500/10',
        borderColor: 'border-zinc-500/30',
        components: [
            { name: 'Docker Compose', full: 'Local compose stack (12 services)' },
            { name: 'Prometheus', full: 'Metrics collection' },
            { name: 'Grafana', full: 'Dashboards & alerts' },
        ],
    },
];

export default function ArchitecturePage() {
    return (
        <div className="min-h-screen bg-zinc-950">
            <Header />

            {/* Hero */}
            <section className="pt-32 pb-16">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl md:text-5xl font-bold text-zinc-100 mb-4">
                            System Architecture
                        </h1>
                        <p className="text-xl text-zinc-400">
                            A local-first architecture that keeps evidence close to the code.
                            Heavy services run locally; the demo is intentionally lightweight.
                        </p>
                    </div>
                </div>
            </section>

            {/* Visual Data Flow */}
            <section className="py-12">
                <div className="max-w-5xl mx-auto px-6">
                    <h2 className="text-2xl font-bold text-zinc-100 mb-8 text-center">Data Flow</h2>

                    <div className="relative bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8">
                        <div className="space-y-6">
                            {/* Client Layer */}
                            <div className="flex justify-center gap-4 flex-wrap">
                                {['Transaction', 'Card', 'Device', 'Location'].map((item) => (
                                    <div key={item} className="px-6 py-3 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-zinc-300 font-medium">
                                        {item}
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-center"><ArrowDown className="w-6 h-6 text-zinc-600" /></div>

                            {/* Ingestion */}
                            <div className="flex justify-center">
                                <div className="px-8 py-4 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-center">
                                    <p className="text-zinc-300 font-semibold">Kafka + Flink CEP</p>
                                    <p className="text-zinc-500 text-sm">Event streaming & pattern detection (local)</p>
                                </div>
                            </div>

                            <div className="flex justify-center gap-8">
                                <ArrowDown className="w-6 h-6 text-zinc-600" />
                                <ArrowDown className="w-6 h-6 text-zinc-600" />
                            </div>

                            {/* Processing */}
                            <div className="flex justify-center gap-8 flex-wrap">
                                <div className="px-6 py-3 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-center">
                                    <p className="text-zinc-300 font-medium">Feature Store</p>
                                    <p className="text-zinc-500 text-xs">Feast + Redis cache</p>
                                </div>
                                <div className="px-6 py-3 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-center">
                                    <p className="text-zinc-300 font-medium">ML Scoring</p>
                                    <p className="text-zinc-500 text-xs">XGBoost serving, GAT training</p>
                                </div>
                                <div className="px-6 py-3 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-center">
                                    <p className="text-zinc-300 font-medium">Neo4j Analysis</p>
                                    <p className="text-zinc-500 text-xs">PageRank + communities (local)</p>
                                </div>
                            </div>

                            <div className="flex justify-center"><ArrowDown className="w-6 h-6 text-zinc-600" /></div>

                            {/* Output */}
                            <div className="flex justify-center">
                                <div className="px-8 py-4 bg-zinc-500/10 border border-zinc-500/30 rounded-xl text-center">
                                    <p className="text-zinc-300 font-semibold">Dashboard + SHAP + RAG</p>
                                    <p className="text-zinc-500 text-sm">Case queue, explainability, copilot</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Architecture Layers */}
            <section className="py-16">
                <div className="max-w-7xl mx-auto px-6">
                    <h2 className="text-2xl font-bold text-zinc-100 mb-12 text-center">Architecture Layers</h2>

                    <div className="space-y-6">
                        {layers.map((layer, index) => (
                            <div key={layer.name}>
                                <div className={`${layer.bgColor} border ${layer.borderColor} rounded-2xl p-6`}>
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${layer.color} flex items-center justify-center`}>
                                            <layer.icon className="w-6 h-6 text-white" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-zinc-100">{layer.name}</h3>
                                    </div>

                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                        {layer.components.map((comp) => (
                                            <div key={comp.name} className="bg-zinc-900/80 rounded-xl p-4 flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center flex-shrink-0">
                                                    <img
                                                        src={getLogoUrl(comp.name)}
                                                        alt={comp.name}
                                                        className="w-5 h-5 opacity-80"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = 'none';
                                                        }}
                                                    />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-medium text-zinc-200 truncate">{comp.name}</p>
                                                    <p className="text-xs text-zinc-500 truncate">{comp.full}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {index < layers.length - 1 && (
                                    <div className="flex justify-center py-2">
                                        <ArrowDown className="w-6 h-6 text-zinc-700" />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Role Coverage */}
            <section className="py-16 bg-zinc-900/30">
                <div className="max-w-7xl mx-auto px-6">
                    <h2 className="text-2xl font-bold text-zinc-100 mb-10 text-center">Capabilities by Role</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            {
                                title: 'Data Engineering',
                                icon: Cpu,
                                items: ['Kafka ingestion flow', 'Flink CEP patterns', 'Spark feature jobs'],
                            },
                            {
                                title: 'ML Engineering',
                                icon: Brain,
                                items: ['XGBoost scoring', 'GAT training scripts', 'SHAP explainability'],
                            },
                            {
                                title: 'Full Stack',
                                icon: Monitor,
                                items: ['Next.js dashboard', 'GraphQL queries', 'D3 network graphs'],
                            },
                            {
                                title: 'MLOps',
                                icon: Cloud,
                                items: ['MLflow tracking', 'Prometheus metrics', 'Docker Compose stack'],
                            },
                        ].map((role) => (
                            <div key={role.title} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                                <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center mb-4">
                                    <role.icon className="w-5 h-5 text-zinc-200" />
                                </div>
                                <h3 className="text-lg font-semibold text-zinc-100 mb-3">{role.title}</h3>
                                <ul className="text-sm text-zinc-400 space-y-2">
                                    {role.items.map((item) => (
                                        <li key={item}>- {item}</li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Free-tier Demo Targets */}
            <section className="py-16">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-8">
                        <div className="flex items-center gap-3 mb-6">
                            <Cloud className="w-6 h-6 text-zinc-200" />
                            <h3 className="text-xl font-semibold text-zinc-100">Free-tier Demo Targets</h3>
                            <span className="ml-auto text-xs text-zinc-500">Planned deployment map</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {[
                                { name: 'Supabase', desc: 'Postgres + pgvector for hosted demo data' },
                                { name: 'Upstash', desc: 'Serverless Redis for cache and rate limits' },
                                { name: 'Railway', desc: 'API + frontend hosting on free tier' },
                            ].map((item) => (
                                <div key={item.name} className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
                                    <p className="text-zinc-100 font-medium">{item.name}</p>
                                    <p className="text-sm text-zinc-500 mt-1">{item.desc}</p>
                                </div>
                            ))}
                        </div>
                        <p className="text-xs text-zinc-500 mt-4">
                            Heavy services (Kafka, Neo4j, Flink) stay local for the full pipeline.
                        </p>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <Link
                        href="/stack"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900 border border-zinc-700 text-zinc-100 rounded-xl font-medium hover:bg-zinc-800 transition-all"
                    >
                        Explore Tech Stack
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </section>

            <Footer />
        </div>
    );
}
