import knowledge from "@/lib/project-guide/knowledge.generated.json";
import {
  LIMITS,
  answerQuestion,
  createRetriever,
  sanitiseHistory,
  type FetchLike,
  type KnowledgeBase,
  type LlmConfig,
} from "@/lib/project-guide/core";
import { ASSISTANT_CONFIG } from "@/lib/project-guide/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const retriever = createRetriever(knowledge as unknown as KnowledgeBase, { homeProject: ASSISTANT_CONFIG.homeProject });

const persona = {
  homeProject: ASSISTANT_CONFIG.homeProject,
  ownerName: ASSISTANT_CONFIG.ownerName,
  contactLine: ASSISTANT_CONFIG.contactLine,
};

/**
 * Any OpenAI-compatible chat completions endpoint works. Defaults target Groq;
 * GROQ_API_KEY is accepted so an existing key can be reused. With no key the
 * assistant still answers, extractively, from the same retrieved passages.
 */
function llmConfig(): LlmConfig | null {
  const apiKey = process.env.ASSISTANT_LLM_API_KEY || process.env.GROQ_API_KEY;
  if (!apiKey || process.env.ASSISTANT_LLM_DISABLED === "1") return null;
  return {
    apiKey,
    baseUrl: process.env.ASSISTANT_LLM_BASE_URL || "https://api.groq.com/openai/v1",
    model: process.env.ASSISTANT_LLM_MODEL || "openai/gpt-oss-120b",
    timeoutMs: Number(process.env.ASSISTANT_LLM_TIMEOUT_MS || 12000),
  };
}

// Best-effort, per-instance rate limit: 20 questions per minute per client.
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 20;
const hits = new Map<string, number[]>();

function rateLimited(key: string): boolean {
  const now = Date.now();
  const recent = (hits.get(key) || []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(key, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > MAX_PER_WINDOW;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export async function GET(): Promise<Response> {
  return json({
    status: "ok",
    project: ASSISTANT_CONFIG.homeProject,
    chunks: retriever.size,
    vocabulary: retriever.vocabularySize,
    generatedFrom: (knowledge as unknown as KnowledgeBase).generatedFrom,
    llmConfigured: llmConfig() !== null,
  });
}

export async function POST(req: Request): Promise<Response> {
  const client = (req.headers.get("x-forwarded-for") || "local").split(",")[0].trim();
  if (rateLimited(client)) {
    return json({ error: "Too many questions in a minute. Please wait a moment and try again." }, 429);
  }

  let body: { question?: unknown; history?: unknown };
  try {
    body = (await req.json()) as { question?: unknown; history?: unknown };
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const question = typeof body.question === "string" ? body.question.trim() : "";
  if (!question) return json({ error: "Ask a question first." }, 400);
  if (question.length > LIMITS.maxQuestionChars) {
    return json({ error: `Please keep questions under ${LIMITS.maxQuestionChars} characters.` }, 413);
  }

  try {
    const result = await answerQuestion(question, sanitiseHistory(body.history), {
      retriever,
      persona,
      llm: llmConfig(),
      fetchImpl: fetch as unknown as FetchLike,
      onLlmError: (error) => console.warn("[project-guide] LLM unavailable, using extractive answer:", String(error)),
    });
    return json(result);
  } catch (error) {
    console.error("[project-guide] failed:", error);
    return json({ error: "The assistant hit an unexpected error. Please try again." }, 500);
  }
}
