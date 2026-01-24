'use client';

import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import Link from 'next/link';
import { ArrowRight, Play, ExternalLink } from 'lucide-react';

const getLogoUrl = (name: string) => {
    const slugMap: Record<string, string> = {
        'Next.js 16': 'nextdotjs',
        'React 18': 'react',
        'TypeScript': 'typescript',
        'D3.js': 'd3dotjs',
        'Tailwind CSS': 'tailwindcss',
        'Radix UI': 'radixui',
        'React Query': 'reactquery',
        'FastAPI': 'fastapi',
        'Strawberry': 'graphql',
        'Pydantic': 'pydantic',
        'structlog': 'python',
        'Apache Kafka': 'apachekafka',
        'Apache Flink': 'apacheflink',
        'Apache Spark': 'apachespark',
        'Airflow': 'apacheairflow',
        'Great Expectations': 'python',
        'Feast': 'python',
        'Avro': 'apachekafka',
        'XGBoost': 'python',
        'PyTorch': 'pytorch',
        'PyTorch Geometric': 'pytorch',
        'SHAP': 'python',
        'MLflow': 'mlflow',
        'Optuna': 'python',
        'Evidently': 'python',
        'scikit-learn': 'scikitlearn',
        'PostgreSQL': 'postgresql',
        'Neo4j': 'neo4j',
        'Redis': 'redis',
        'Docker': 'docker',
        'Docker Compose': 'docker',
        'Prometheus': 'prometheus',
        'Grafana': 'grafana',
        'GitHub Actions': 'githubactions',
        'Terraform': 'terraform',
        'Groq': 'groq',
        'Ollama': 'ollama',
        'OpenAI Compatible': 'openai',
        'SentenceTransformers': 'python',
        'pgvector': 'postgresql',
        'Supabase': 'supabase',
        'Upstash': 'upstash',
        'Railway': 'railway',
    };
    const slug = slugMap[name] || name.toLowerCase().replace(/[^a-z0-9]/g, '');
    return `https://cdn.simpleicons.org/${slug}/white`;
};

const categories = [
    {
        name: 'Frontend',
        description: 'Modern UI stack with data visualization',
        color: 'from-zinc-100 to-zinc-400',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'Next.js 16', description: 'React framework with App Router', url: 'https://nextjs.org' },
            { name: 'React 18', description: 'React with hooks', url: 'https://react.dev' },
            { name: 'TypeScript', description: 'Static typing for better DX', url: 'https://typescriptlang.org' },
            { name: 'D3.js', description: 'Network graph visualization', url: 'https://d3js.org' },
            { name: 'Tailwind CSS', description: 'Utility-first CSS', url: 'https://tailwindcss.com' },
            { name: 'Radix UI', description: 'Accessible UI primitives', url: 'https://www.radix-ui.com' },
            { name: 'React Query', description: 'Server-state management', url: 'https://tanstack.com/query' },
        ],
    },
    {
        name: 'Backend',
        description: 'High-performance Python APIs and caching',
        color: 'from-zinc-200 to-zinc-500',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'FastAPI', description: 'Modern Python web framework', url: 'https://fastapi.tiangolo.com' },
            { name: 'Strawberry', description: 'GraphQL schema + resolvers', url: 'https://strawberry.rocks' },
            { name: 'Pydantic', description: 'Data validation using types', url: 'https://pydantic.dev' },
            { name: 'Redis', description: 'Feature cache + fast lookups', url: 'https://redis.io' },
            { name: 'structlog', description: 'Structured JSON logging', url: 'https://www.structlog.org' },
        ],
    },
    {
        name: 'Data Engineering',
        description: 'Real-time streaming pipelines',
        color: 'from-white to-zinc-400',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'Apache Kafka', description: 'Event streaming platform', url: 'https://kafka.apache.org' },
            { name: 'Apache Flink', description: 'CEP fraud pattern detection', url: 'https://flink.apache.org' },
            { name: 'Apache Spark', description: 'Feature engineering jobs', url: 'https://spark.apache.org' },
            { name: 'Feast', description: 'Online/offline feature store', url: 'https://feast.dev' },
            { name: 'Airflow', description: 'Pipeline orchestration', url: 'https://airflow.apache.org' },
            { name: 'Great Expectations', description: 'Data quality checks', url: 'https://greatexpectations.io' },
            { name: 'Avro', description: 'Schema-backed payloads', url: 'https://avro.apache.org' },
        ],
    },
    {
        name: 'Machine Learning',
        description: 'Ensemble models with explainability',
        color: 'from-zinc-300 to-zinc-600',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'XGBoost', description: 'Gradient boosting ensemble', url: 'https://xgboost.readthedocs.io' },
            { name: 'PyTorch', description: 'Deep learning framework', url: 'https://pytorch.org' },
            { name: 'PyTorch Geometric', description: 'Graph Attention Networks', url: 'https://pytorch-geometric.readthedocs.io' },
            { name: 'SHAP', description: 'Explainable AI', url: 'https://shap.readthedocs.io' },
            { name: 'MLflow', description: 'ML lifecycle management', url: 'https://mlflow.org' },
            { name: 'Optuna', description: 'Hyperparameter tuning', url: 'https://optuna.org' },
            { name: 'Evidently', description: 'Data & model drift detection', url: 'https://evidentlyai.com' },
            { name: 'scikit-learn', description: 'ML in Python', url: 'https://scikit-learn.org' },
        ],
    },
    {
        name: 'AI + RAG',
        description: 'Retrieval-augmented investigator copilot',
        color: 'from-zinc-200 to-zinc-400',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'Groq', description: 'Hosted LLM inference', url: 'https://groq.com' },
            { name: 'Ollama', description: 'Local LLM runtime', url: 'https://ollama.com' },
            { name: 'OpenAI Compatible', description: 'OpenAI-style API support', url: 'https://platform.openai.com/docs/api-reference' },
            { name: 'SentenceTransformers', description: 'Embedding models', url: 'https://www.sbert.net' },
            { name: 'pgvector', description: 'Vector search in Postgres', url: 'https://github.com/pgvector/pgvector' },
        ],
    },
    {
        name: 'Databases',
        description: 'Multi-model data storage',
        color: 'from-zinc-400 to-zinc-700',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'PostgreSQL', description: 'Transactional database', url: 'https://postgresql.org' },
            { name: 'Neo4j', description: 'Graph database for networks', url: 'https://neo4j.com' },
            { name: 'Redis', description: 'Feature cache & sessions', url: 'https://redis.io' },
        ],
    },
    {
        name: 'Deployment (Free Tier)',
        description: 'Planned free-tier targets for hosted demo',
        color: 'from-zinc-100 to-zinc-300',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'Supabase', description: 'Planned: Postgres + pgvector', url: 'https://supabase.com' },
            { name: 'Upstash', description: 'Planned: serverless Redis', url: 'https://upstash.com' },
            { name: 'Railway', description: 'Planned: deploy API + frontend', url: 'https://railway.app' },
        ],
    },
    {
        name: 'DevOps',
        description: 'Containerization and monitoring',
        color: 'from-zinc-100 to-zinc-300',
        borderColor: 'border-zinc-500/50',
        tools: [
            { name: 'Docker', description: 'Container platform', url: 'https://docker.com' },
            { name: 'Docker Compose', description: 'Multi-container orchestration', url: 'https://docs.docker.com/compose' },
            { name: 'Prometheus', description: 'Metrics collection', url: 'https://prometheus.io' },
            { name: 'Grafana', description: 'Dashboards & alerts', url: 'https://grafana.com' },
            { name: 'GitHub Actions', description: 'CI workflow automation', url: 'https://github.com/features/actions' },
            { name: 'Terraform', description: 'Infrastructure template', url: 'https://www.terraform.io' },
        ],
    },
];

export default function TechStackPage() {
    return (
        <div className="min-h-screen bg-zinc-950">
            <Header />

            {/* Hero */}
            <section className="pt-32 pb-16">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl md:text-5xl font-bold text-zinc-100 mb-4">
                            Technology Stack
                        </h1>
                        <p className="text-xl text-zinc-400">
                            Evidence-first stack with local execution and planned free-tier targets.
                        </p>
                    </div>
                </div>
            </section>

            {/* Stack Principles */}
            <section className="py-10">
                <div className="max-w-6xl mx-auto px-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[
                            {
                                title: 'Local-first pipeline',
                                desc: 'Kafka, Neo4j, Flink, and MLflow run locally to preserve full functionality.',
                            },
                            {
                                title: 'Free-tier demo targets',
                                desc: 'Supabase, Upstash, and Railway are planned for the hosted demo footprint.',
                            },
                            {
                                title: 'Evidence-backed claims',
                                desc: 'Test logs and metrics artifacts live in docs/evidence for verification.',
                            },
                        ].map((item) => (
                            <div key={item.title} className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                                <h3 className="text-lg font-semibold text-zinc-100 mb-2">{item.title}</h3>
                                <p className="text-sm text-zinc-500">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Tech Categories */}
            <section className="py-12">
                <div className="max-w-7xl mx-auto px-6 space-y-16">
                    {categories.map((category) => (
                        <div key={category.name}>
                            <div className="flex items-center gap-4 mb-8">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${category.color} flex items-center justify-center`}>
                                    <span className="text-xl font-bold text-white">{category.name.charAt(0)}</span>
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-zinc-100">{category.name}</h2>
                                    <p className="text-zinc-500">{category.description}</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {category.tools.map((tool) => (
                                    <a
                                        key={tool.name}
                                        href={tool.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className={`group relative bg-zinc-900/50 border ${category.borderColor} rounded-xl p-5 hover:bg-zinc-900 hover:border-opacity-100 transition-all flex items-start gap-4`}
                                    >
                                        <div className="w-10 h-10 rounded-lg bg-zinc-800/80 flex items-center justify-center flex-shrink-0 overflow-hidden">
                                            <img
                                                src={getLogoUrl(tool.name)}
                                                alt={tool.name}
                                                className="w-6 h-6 opacity-80 group-hover:opacity-100 transition-opacity"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-semibold text-zinc-100 group-hover:text-zinc-300 transition-colors truncate">
                                                    {tool.name}
                                                </h3>
                                                <ExternalLink className="w-3 h-3 text-zinc-600 group-hover:text-zinc-300 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                                            </div>
                                            <p className="text-sm text-zinc-500 leading-relaxed mt-1">
                                                {tool.description}
                                            </p>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Stats */}
            <section className="py-16 bg-zinc-900/30">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        {[
                            { value: '30+', label: 'Libraries & Tools' },
                            { value: '12', label: 'Local Services' },
                            { value: '2', label: 'Model Families' },
                            { value: '3', label: 'Primary Stores' },
                        ].map((stat) => (
                            <div key={stat.label} className="text-center">
                                <p className="text-4xl font-bold bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
                                    {stat.value}
                                </p>
                                <p className="text-zinc-500">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-16">
                <div className="max-w-4xl mx-auto px-6 text-center">
                    <Link
                        href="/demo"
                        className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-zinc-100 to-zinc-400 text-zinc-900 rounded-xl font-semibold text-lg hover:from-white hover:to-zinc-300 transition-all shadow-xl shadow-zinc-500/20"
                    >
                        <Play className="w-5 h-5" />
                        Try the Demo
                    </Link>
                </div>
            </section>

            <Footer />
        </div>
    );
}
