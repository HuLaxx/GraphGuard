"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { queryRag, fetchRagIndexes, fetchRagStatus, ingestRepo, RagResponse, RagStatus } from "@/lib/rag-client";

interface Message {
    role: "user" | "assistant";
    content: string;
    sources?: RagResponse["sources"];
}

export function RagAssistant() {
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [indexing, setIndexing] = useState(false);
    const [indexNotice, setIndexNotice] = useState<string | null>(null);
    const [status, setStatus] = useState<RagStatus | null>(null);
    const [indexes, setIndexes] = useState<string[]>([]);
    const [activeIndex, setActiveIndex] = useState<string | undefined>(undefined);

    useEffect(() => {
        fetchRagIndexes()
            .then((data) => {
                const list = data?.indexes || [];
                setIndexes(list);
                if (!activeIndex && list.length > 0) {
                    setActiveIndex(list[0]);
                }
            })
            .catch(() => {
                setIndexes([]);
            });
    }, [activeIndex]);

    useEffect(() => {
        fetchRagStatus()
            .then(setStatus)
            .catch(() => setStatus(null));
    }, []);

    const canAsk = question.trim().length > 2 && !loading;
    const allowIngest = process.env.NEXT_PUBLIC_RAG_ALLOW_INGEST === "true";

    const handleAsk = async () => {
        if (!canAsk) return;
        const userMessage: Message = { role: "user", content: question };
        setMessages((prev) => [...prev, userMessage]);
        setQuestion("");
        setLoading(true);
        setError(null);

        try {
            const response = await queryRag(userMessage.content, activeIndex);
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: response.answer,
                    sources: response.sources,
                },
            ]);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "RAG request failed");
        } finally {
            setLoading(false);
        }
    };

    const handleIngest = async () => {
        if (!allowIngest || indexing) return;
        setIndexing(true);
        setIndexNotice(null);
        try {
            const response = await ingestRepo(activeIndex);
            setIndexNotice(
                `Indexed ${response.files_indexed} files (${response.indexed_chunks} chunks) into ${response.index}`
            );
        } catch (err: unknown) {
            setIndexNotice(err instanceof Error ? err.message : "Indexing failed");
        } finally {
            setIndexing(false);
        }
    };

    return (
        <Card>
            <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <CardTitle className="text-lg">Investigator Copilot (RAG)</CardTitle>
                        <p className="text-xs text-zinc-500 mt-1">
                            Local-first retrieval with optional Groq/Ollama generation
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {allowIngest && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleIngest}
                                disabled={indexing}
                            >
                                {indexing ? "Indexing..." : "Index Repo"}
                            </Button>
                        )}
                        <select
                            className="bg-zinc-900 text-zinc-300 border border-zinc-700 rounded-lg text-xs px-2 py-1"
                            value={activeIndex || ""}
                            onChange={(e) => setActiveIndex(e.target.value)}
                        >
                            {indexes.length === 0 && <option value="">default</option>}
                            {indexes.map((idx) => (
                                <option key={idx} value={idx}>
                                    {idx}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 min-h-[220px] max-h-[280px] overflow-y-auto text-sm">
                    {messages.length === 0 && (
                        <p className="text-zinc-500">
                            Ask about pipeline flow, model training, or infra setup.
                        </p>
                    )}
                    <div className="space-y-4">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={msg.role === "user" ? "text-right" : "text-left"}>
                                <div className={msg.role === "user"
                                    ? "inline-block bg-zinc-800 text-zinc-100 px-3 py-2 rounded-lg"
                                    : "inline-block bg-zinc-900 text-zinc-200 px-3 py-2 rounded-lg"}
                                >
                                    {msg.content}
                                </div>
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="mt-2 text-xs text-zinc-500 space-y-1">
                                        {msg.sources.slice(0, 4).map((source) => (
                                            <div key={source.id}>
                                                • {typeof source.metadata?.source === "string" ? source.metadata.source : source.id} (score {source.score.toFixed(2)})
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {error && (
                    <div className="text-xs text-red-400">{error}</div>
                )}

                {indexNotice && (
                    <div className="text-xs text-emerald-400">{indexNotice}</div>
                )}

                {status && (
                    <div className="text-xs text-zinc-500 space-y-1">
                        <div>Store: {status.vector_store}</div>
                        <div>Embeddings: {status.embeddings_provider}</div>
                        <div>LLM: {status.llm_provider} · {status.llm_model}</div>
                        {status.auto_index_enabled && (
                            <div>Auto-index: {status.auto_index_root} → {status.auto_index_index}</div>
                        )}
                    </div>
                )}

                <div className="flex gap-2">
                    <input
                        className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"
                        placeholder="Ask about the system..."
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") handleAsk();
                        }}
                    />
                    <Button onClick={handleAsk} disabled={!canAsk}>
                        {loading ? "Thinking..." : "Ask"}
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
