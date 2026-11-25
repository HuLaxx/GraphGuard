"use client";

import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import type { AssistantAnswer, AssistantSource } from "@/lib/project-guide/core";
import { ASSISTANT_CONFIG } from "@/lib/project-guide/config";
import "./project-guide.css";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: AssistantSource[];
  mode?: AssistantAnswer["mode"];
  error?: boolean;
  question?: string;
}

const STORAGE_KEY = `project-guide:${ASSISTANT_CONFIG.homeProject}:v1`;
const PROJECT_NAMES: Record<string, string> = {
  fleetflow: "FleetFlow",
  graphguard: "GraphGuard",
  sentinance: "Sentinance",
  profile: "Profile",
};

function loadMessages(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    return saved ? (JSON.parse(saved) as Message[]).slice(-20) : [];
  } catch {
    return [];
  }
}

let idCounter = 0;
const nextId = () => `m${Date.now().toString(36)}${(idCounter++).toString(36)}`;

/* ---------------------------------------------------------------------- */
/* Safe markdown-lite rendering (no HTML injection)                        */
/* ---------------------------------------------------------------------- */

function renderInline(text: string, sources: AssistantSource[] | undefined, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[\d{1,2}\]|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) out.push(text.slice(last, match.index));
    const token = match[0];
    const key = `${keyBase}-${i++}`;
    if (token.startsWith("**")) {
      out.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      out.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (/^\[\d{1,2}\]$/.test(token)) {
      const n = Number(token.slice(1, -1));
      const source = sources?.find((s) => s.n === n);
      out.push(
        source ? (
          <a key={key} className="rka-cite" href={source.url} target="_blank" rel="noopener noreferrer" title={`${source.title}${source.heading ? ` · ${source.heading}` : ""}`}>
            {n}
          </a>
        ) : null,
      );
    } else {
      const m = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(token);
      if (m) {
        out.push(
          <a key={key} href={m[2]} target="_blank" rel="noopener noreferrer">
            {m[1]}
          </a>,
        );
      }
    }
    last = match.index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

type Block = { kind: "p"; text: string } | { kind: "h"; text: string } | { kind: "ul" | "ol"; items: string[] };

/** Plain parser (not a component) so render stays pure. */
function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let para: string[] = [];
  let list: { kind: "ul" | "ol"; items: string[] } | null = null;
  for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trim();
    const bullet = /^[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line);
    const heading = /^#{1,4}\s+(.*)$/.exec(line);
    const item = bullet ? bullet[1] : numbered ? numbered[1] : null;
    if (para.length && (!line || item !== null || heading)) {
      blocks.push({ kind: "p", text: para.join(" ") });
      para = [];
    }
    if (list && (!line || item === null || list.kind !== (numbered ? "ol" : "ul"))) {
      blocks.push(list);
      list = null;
    }
    if (!line) continue;
    if (item !== null) {
      if (!list) list = { kind: numbered ? "ol" : "ul", items: [] };
      list.items.push(item);
    } else if (heading) {
      blocks.push({ kind: "h", text: heading[1] });
    } else {
      para.push(line);
    }
  }
  if (para.length) blocks.push({ kind: "p", text: para.join(" ") });
  if (list) blocks.push(list);
  return blocks;
}

function RichText({ text, sources }: { text: string; sources?: AssistantSource[] }) {
  return (
    <div className="rka-rich">
      {toBlocks(text).map((block, i) => {
        const k = `b${i}`;
        if (block.kind === "p") return <p key={k}>{renderInline(block.text, sources, k)}</p>;
        if (block.kind === "h") return <p key={k} className="rka-subhead">{renderInline(block.text, sources, k)}</p>;
        const items = block.items.map((item, j) => <li key={`${k}-${j}`}>{renderInline(item, sources, `${k}-${j}`)}</li>);
        return block.kind === "ol" ? <ol key={k}>{items}</ol> : <ul key={k}>{items}</ul>;
      })}
    </div>
  );
}

/* ---------------------------------------------------------------------- */
/* Widget                                                                  */
/* ---------------------------------------------------------------------- */

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9L12 2.5z" fill="currentColor" />
      <path d="M18.5 15l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2z" fill="currentColor" opacity=".7" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <path d="M4 12l16-8-6 16-2.5-6.5L4 12z" fill="currentColor" />
    </svg>
  );
}

function Thinking() {
  return (
    <div className="rka-msg rka-msg-assistant" role="status">
      <div className="rka-thinking" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <span className="rka-thinking-label">Searching the project docs…</span>
    </div>
  );
}

function Sources({ sources }: { sources: AssistantSource[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="rka-sources">
      <button type="button" className="rka-sources-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {open ? "Hide" : "Show"} {sources.length} source{sources.length === 1 ? "" : "s"}
      </button>
      {open && (
        <ol className="rka-source-list">
          {sources.map((s) => (
            <li key={s.n}>
              <a href={s.url} target="_blank" rel="noopener noreferrer">
                <span className="rka-source-n">{s.n}</span>
                <span className="rka-source-text">
                  <span className="rka-source-project">{PROJECT_NAMES[s.project] || s.project}</span>
                  <span className="rka-source-title">{s.title}</span>
                  {s.heading && <span className="rka-source-heading">{s.heading}</span>}
                </span>
              </a>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function ProjectGuide() {
  const pathname = usePathname() || "/";
  const [open, setOpen] = useState(false);
  // Messages only render inside the panel, which is closed on first paint, so
  // reading sessionStorage in the initialiser cannot cause a hydration mismatch.
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const panelId = useId();
  const titleId = useId();
  const inputId = useId();
  const launcherRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const hidden = ASSISTANT_CONFIG.hiddenPaths.some((p) => pathname === p || pathname.startsWith(`${p}/`));

  useEffect(() => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-20)));
    } catch {
      /* storage unavailable */
    }
  }, [messages]);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, pending, open]);

  useEffect(() => {
    if (!open) return undefined;
    const t = window.setTimeout(() => inputRef.current?.focus(), 60);
    return () => window.clearTimeout(t);
  }, [open]);

  const close = useCallback(() => {
    setOpen(false);
    window.setTimeout(() => launcherRef.current?.focus(), 0);
  }, []);

  const ask = useCallback(
    async (raw: string) => {
      const question = raw.trim();
      if (!question || pending) return;
      const history = messages
        .filter((m) => !m.error)
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));
      setMessages((prev) => [...prev, { id: nextId(), role: "user", content: question }]);
      setInput("");
      setPending(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const res = await fetch("/api/project-guide", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, history }),
          signal: controller.signal,
        });
        const data = (await res.json().catch(() => ({}))) as Partial<AssistantAnswer> & { error?: string };
        if (!res.ok || !data.answer) {
          throw new Error(data.error || `The assistant returned HTTP ${res.status}.`);
        }
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", content: data.answer as string, sources: data.sources || [], mode: data.mode },
        ]);
      } catch (error) {
        if ((error as { name?: string }).name === "AbortError") return;
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: error instanceof Error ? error.message : "Something went wrong.",
            error: true,
            question,
          },
        ]);
      } finally {
        setPending(false);
        abortRef.current = null;
      }
    },
    [messages, pending],
  );

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(input);
  };

  const onInputKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(input);
    }
  };

  const onPanelKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      close();
    }
  };

  const retry = (message: Message) => {
    if (!message.question) return;
    // Drop the failed reply and the question it answered; ask() re-adds the question.
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === message.id);
      if (idx < 0) return prev;
      const from = idx > 0 && prev[idx - 1].role === "user" ? idx - 1 : idx;
      return [...prev.slice(0, from), ...prev.slice(idx + 1)];
    });
    void ask(message.question);
  };

  if (hidden) return null;

  return (
    <div className="rka-root" data-theme={ASSISTANT_CONFIG.theme} data-open={open ? "true" : "false"}>
      <button
        ref={launcherRef}
        type="button"
        className="rka-launcher"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span className="rka-launcher-icon">{open ? <CloseIcon /> : <SparkIcon />}</span>
        <span className="rka-launcher-label">{open ? "Close" : ASSISTANT_CONFIG.launcherLabel}</span>
      </button>

      {open && (
        <div id={panelId} className="rka-panel" role="dialog" aria-modal="false" aria-labelledby={titleId} onKeyDown={onPanelKeyDown}>
          <header className="rka-header">
            <div className="rka-header-motif" aria-hidden="true" />
            <div className="rka-header-text">
              <p className="rka-eyebrow">{ASSISTANT_CONFIG.eyebrow}</p>
              <h2 id={titleId} className="rka-title">
                {ASSISTANT_CONFIG.title}
              </h2>
              <p className="rka-subtitle">{ASSISTANT_CONFIG.subtitle}</p>
            </div>
            <div className="rka-header-actions">
              {messages.length > 0 && (
                <button type="button" className="rka-icon-btn rka-clear" onClick={() => setMessages([])} disabled={pending}>
                  New chat
                </button>
              )}
              <button type="button" className="rka-icon-btn" onClick={close} aria-label="Close project guide">
                <CloseIcon />
              </button>
            </div>
          </header>

          <div ref={logRef} className="rka-log" role="log" aria-live="polite" aria-relevant="additions">
            {messages.length === 0 && (
              <div className="rka-empty">
                <p className="rka-greeting">{ASSISTANT_CONFIG.greeting}</p>
                <p className="rka-empty-label">Try one of these</p>
                <div className="rka-suggestions">
                  {ASSISTANT_CONFIG.suggestions.map((s) => (
                    <button key={s} type="button" className="rka-chip" onClick={() => void ask(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.id} className={`rka-msg rka-msg-${m.role}${m.error ? " rka-msg-error" : ""}`}>
                {m.role === "user" ? (
                  <p>{m.content}</p>
                ) : m.error ? (
                  <div className="rka-error">
                    <p>{m.content}</p>
                    {m.question && (
                      <button type="button" className="rka-retry" onClick={() => retry(m)} disabled={pending}>
                        Try again
                      </button>
                    )}
                  </div>
                ) : (
                  <>
                    <RichText text={m.content} sources={m.sources} />
                    {m.mode === "extractive" && <p className="rka-mode">Quoted from the docs (AI summary unavailable)</p>}
                    {m.sources && <Sources sources={m.sources} />}
                  </>
                )}
              </div>
            ))}

            {pending && <Thinking />}
          </div>

          <form className="rka-form" onSubmit={onSubmit}>
            <label htmlFor={inputId} className="rka-sr-only">
              Ask a question about {ASSISTANT_CONFIG.projectName} or Rahul
            </label>
            <textarea
              id={inputId}
              ref={inputRef}
              className="rka-input"
              rows={1}
              maxLength={600}
              placeholder={ASSISTANT_CONFIG.placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onInputKeyDown}
            />
            <button type="submit" className="rka-send" disabled={pending || !input.trim()} aria-label="Send question">
              <SendIcon />
            </button>
          </form>
          <p className="rka-footnote">Answers come only from the repo docs and cite their sources. Synthetic and CI results are labelled as such.</p>
        </div>
      )}
    </div>
  );
}

export default ProjectGuide;
