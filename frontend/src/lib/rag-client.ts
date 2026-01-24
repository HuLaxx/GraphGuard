export type RagSource = {
    id: string;
    score: number;
    metadata: Record<string, any>;
    preview: string;
};

export type RagResponse = {
    answer: string;
    sources: RagSource[];
    model: string;
    index: string;
    latency_ms: number;
};

export type RagIngestResponse = {
    indexed_chunks: number;
    files_indexed: number;
    skipped_files: number;
    index: string;
};

export type RagStatus = {
    enabled: boolean;
    vector_store: string;
    embeddings_provider: string;
    llm_provider: string;
    llm_model: string;
    index_dir: string;
    auto_index_enabled?: boolean;
    auto_index_root?: string;
    auto_index_index?: string;
};

const DEFAULT_RAG_URL = "http://localhost:8000";

export function getRagBaseUrl() {
    return process.env.NEXT_PUBLIC_RAG_API_URL || DEFAULT_RAG_URL;
}

export async function fetchRagIndexes() {
    const res = await fetch(`${getRagBaseUrl()}/rag/indexes`);
    if (!res.ok) {
        throw new Error(`RAG indexes failed: ${res.status}`);
    }
    return res.json();
}

export async function fetchRagStatus(): Promise<RagStatus> {
    const res = await fetch(`${getRagBaseUrl()}/rag/status`);
    if (!res.ok) {
        throw new Error(`RAG status failed: ${res.status}`);
    }
    return res.json();
}

export async function queryRag(question: string, index?: string): Promise<RagResponse> {
    const res = await fetch(`${getRagBaseUrl()}/rag/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, index }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `RAG query failed: ${res.status}`);
    }
    return res.json();
}

export async function ingestRepo(index?: string, rootPath = "."): Promise<RagIngestResponse> {
    const res = await fetch(`${getRagBaseUrl()}/rag/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            source_type: "repo",
            root_path: rootPath,
            index,
        }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `RAG ingest failed: ${res.status}`);
    }
    return res.json();
}
