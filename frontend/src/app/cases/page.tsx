"use client";

import { useState, type FormEvent } from "react";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { VerifiedShapChart } from "@/components/review/verified-shap-chart";
import {
    allowedReviewActions, fetchSignedReview, readableAction, shortenHash,
    type ReviewAction, type ReviewCase, type ReviewExplanation, type ReviewIdentity,
} from "@/lib/signed-review";
import {
    Activity, ArrowRight, CheckCircle2, ClipboardList, ExternalLink,
    LockKeyhole, LogOut, RefreshCw, ShieldCheck, TriangleAlert,
} from "lucide-react";

type CaseList = { scope: string; cases: ReviewCase[] };

function dateLabel(value: string): string {
    const ms = Date.parse(value);
    return Number.isFinite(ms) ? new Date(ms).toLocaleString() : "Invalid event time";
}

function HashLine({ label, hash }: { label: string; hash: string }) {
    return (
        <div className="flex items-center justify-between gap-3 border-b border-white/5 py-2 text-xs last:border-0">
            <span className="text-zinc-400">{label}</span>
            <code className="max-w-[60%] truncate font-mono text-zinc-200" title={hash}>
                {shortenHash(hash, 15)}
            </code>
        </div>
    );
}

export default function CasesPage() {
    // Signed token intentionally lives only in component memory. No cookies,
    // localStorage, query strings, hardcoded accounts or fake fallback data.
    const [tokenDraft, setTokenDraft] = useState("");
    const [sessionToken, setSessionToken] = useState("");
    const [identity, setIdentity] = useState<ReviewIdentity | null>(null);
    const [cases, setCases] = useState<ReviewCase[]>([]);
    const [transactionId, setTransactionId] = useState("");
    const [focus, setFocus] = useState<ReviewCase | null>(null);
    const [explanation, setExplanation] = useState<ReviewExplanation | null>(null);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState("");
    const [failure, setFailure] = useState("");

    const resetMessages = () => { setFailure(""); setNotice(""); };
    const errorText = (error: unknown): string =>
        error instanceof Error ? error.message : "Unexpected local review error";

    async function loadCase(caseId: string, token: string) {
        const loaded = await fetchSignedReview<ReviewCase>("cases/" + caseId, token);
        const shap = await fetchSignedReview<ReviewExplanation>(
            "cases/" + caseId + "/explanation", token,
        );
        if (
            loaded.evidence.explanation_sha256 !== shap.explanation_sha256
            || loaded.evidence.model_sha256 !== shap.model_sha256
            || loaded.evidence.source_payload_sha256 !== shap.source_payload_sha256
            || loaded.evidence.feature_snapshot_sha256 !== shap.feature_snapshot_sha256
            || loaded.evidence.score !== shap.verified_model_probability
        ) {
            throw new Error("Case evidence does not match its verified SHAP explanation");
        }
        setFocus(loaded);
        setExplanation(shap);
    }

    async function connect(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        resetMessages();
        setBusy(true);
        try {
            const signed = tokenDraft.trim();
            const who = await fetchSignedReview<ReviewIdentity>("session", signed);
            const list = await fetchSignedReview<CaseList>("cases", signed);
            if (who.scope !== "SYNTHETIC_LOCAL_REVIEW_ONLY" || list.scope !== who.scope) {
                throw new Error("Refusing to display a non-synthetic review response");
            }
            setSessionToken(signed);
            setIdentity(who);
            setCases(list.cases);
            setFocus(null);
            setExplanation(null);
            setTokenDraft("");
            setNotice("Signed local session verified. Select a case or open one from a synthetic transaction.");
        } catch (error) {
            setFailure(errorText(error));
        } finally {
            setBusy(false);
        }
    }

    function disconnect() {
        setSessionToken("");
        setTokenDraft("");
        setIdentity(null);
        setCases([]);
        setFocus(null);
        setExplanation(null);
        setTransactionId("");
        resetMessages();
    }

    async function refresh() {
        if (!sessionToken) return;
        resetMessages();
        setBusy(true);
        try {
            const list = await fetchSignedReview<CaseList>("cases", sessionToken);
            if (list.scope !== "SYNTHETIC_LOCAL_REVIEW_ONLY") {
                throw new Error("Unexpected review data scope");
            }
            setCases(list.cases);
            if (focus) await loadCase(focus.case_id, sessionToken);
        } catch (error) {
            setFailure(errorText(error));
        } finally {
            setBusy(false);
        }
    }

    async function selectCase(caseId: string) {
        resetMessages();
        setBusy(true);
        setExplanation(null);
        try {
            await loadCase(caseId, sessionToken);
        } catch (error) {
            setFocus(null);
            setFailure(errorText(error));
        } finally {
            setBusy(false);
        }
    }

    async function openCase(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!sessionToken || !transactionId.trim()) return;
        resetMessages();
        setBusy(true);
        try {
            const created = await fetchSignedReview<ReviewCase>("cases", sessionToken, {
                method: "POST",
                body: {
                    transaction_id: transactionId.trim(),
                    request_id: "ui-open-" + crypto.randomUUID(),
                },
            });
            const list = await fetchSignedReview<CaseList>("cases", sessionToken);
            setCases(list.cases);
            await loadCase(created.case_id, sessionToken);
            setTransactionId("");
            setNotice("Synthetic review case opened; model and explanation hashes verified.");
        } catch (error) {
            setFailure(errorText(error));
        } finally {
            setBusy(false);
        }
    }

    async function submitAction(action: ReviewAction) {
        if (!focus || !sessionToken) return;
        resetMessages();
        setBusy(true);
        try {
            const updated = await fetchSignedReview<ReviewCase>(
                "cases/" + focus.case_id + "/actions",
                sessionToken,
                {
                    method: "POST",
                    body: {
                        action,
                        expected_version: focus.version,
                        request_id: "ui-review-" + crypto.randomUUID(),
                    },
                },
            );
            await loadCase(updated.case_id, sessionToken);
            const list = await fetchSignedReview<CaseList>("cases", sessionToken);
            setCases(list.cases);
            setNotice("Human review event recorded and audit chain verified.");
        } catch (error) {
            setFailure(errorText(error) + " Refresh the case if its version changed.");
        } finally {
            setBusy(false);
        }
    }

    const actions = focus && identity
        ? allowedReviewActions(focus.status, identity.role) : [];

    return (
        <div className="min-h-screen bg-transparent text-zinc-100">
            <Header />
            <main className="mx-auto max-w-7xl space-y-7 px-4 pb-20 pt-28 sm:px-6">
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">
                    <ShieldCheck className="h-4 w-4" />
                    Local evidence workspace
                    <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-[10px] text-amber-200">
                        Synthetic data only
                    </span>
                </div>
                <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
                    <div className="space-y-3">
                        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                            From a model signal to a <span className="text-violet-300">human decision.</span>
                        </h1>
                        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400 sm:text-base">
                            Inspect real synthetic pipeline evidence, review native SHAP attributions
                            and sign a traceable case action. No automatic accusation, payment
                            decision, or claims about real banking customers.
                        </p>
                    </div>
                    <a
                        href="https://github.com/HuLaxx/GraphGuard/blob/feature/graphguard-local-review-dashboard-2026-11-17/docs/SYNTHETIC_REVIEW_CASES.md"
                        target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 self-start rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:border-violet-300/50 hover:text-white"
                    >
                        Local setup guide <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                    {[
                        { title: "Source", value: "Kafka → Neo4j → PIT", detail: "Synthetic event-time snapshots" },
                        { title: "Evidence", value: "Trained ML + real SHAP", detail: "Hash-verified, non-causal" },
                        { title: "Action", value: "Signed human review", detail: "Append-only local audit" },
                    ].map((item) => (
                        <div key={item.title} className="rounded-2xl border border-white/10 bg-zinc-900/55 p-4">
                            <p className="text-xs font-medium text-zinc-500">{item.title}</p>
                            <p className="mt-1 text-sm font-semibold text-zinc-100">{item.value}</p>
                            <p className="mt-2 text-xs text-zinc-500">{item.detail}</p>
                        </div>
                    ))}
                </div>

                {failure && (
                    <div role="alert" className="flex gap-3 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-100">
                        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                        <p>{failure}</p>
                    </div>
                )}
                {notice && (
                    <div role="status" className="flex gap-3 rounded-2xl border border-emerald-400/25 bg-emerald-400/10 p-4 text-sm text-emerald-100">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                        <p>{notice}</p>
                    </div>
                )}

                {!identity ? (
                    <section className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
                        <form onSubmit={connect} className="space-y-5 rounded-3xl border border-white/10 bg-zinc-900/80 p-6 sm:p-8">
                            <div className="flex items-center gap-3">
                                <div className="rounded-xl border border-violet-300/25 bg-violet-300/10 p-3">
                                    <LockKeyhole className="h-5 w-5 text-violet-200" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-semibold">Connect your local review session</h2>
                                    <p className="text-xs text-zinc-400">Signed demo token · not a production identity service</p>
                                </div>
                            </div>
                            <label className="block space-y-2 text-sm text-zinc-200">
                                <span>Operator-issued reviewer token</span>
                                <input
                                    type="password" autoComplete="off" spellCheck={false}
                                    value={tokenDraft} onChange={(event) => setTokenDraft(event.target.value)}
                                    placeholder="Paste your short-lived signed local token"
                                    required
                                    className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-4 py-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-400"
                                />
                            </label>
                            <button type="submit" disabled={busy || !tokenDraft.trim()}
                                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-200 px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50">
                                <ShieldCheck className="h-4 w-4" /> {busy ? "Verifying…" : "Verify signed session"}
                            </button>
                            <p className="text-xs leading-relaxed text-zinc-500">
                                Tokens remain in this page&apos;s memory only. They are not saved to
                                browser storage and are never inserted into a URL.
                            </p>
                        </form>
                        <div className="space-y-4 rounded-3xl border border-white/10 bg-black/40 p-6 sm:p-8">
                            <h2 className="text-lg font-semibold">What this workspace really connects to</h2>
                            <div className="space-y-4 text-sm text-zinc-400">
                                <p><strong className="text-zinc-200">Local review API:</strong> 127.0.0.1:8765, available only when started by the operator.</p>
                                <p><strong className="text-zinc-200">Known synthetic transaction:</strong> use an ID accepted into the local ledger through the verified ingestion tests.</p>
                                <p><strong className="text-zinc-200">Permissions:</strong> analysts can open and escalate; only signed demo admins can close cases.</p>
                                <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200">
                                    Hosted visitors see no fallback risk scores or fabricated case data. The signed API bridge is disabled in production builds.
                                </p>
                            </div>
                        </div>
                    </section>
                ) : (
                    <section className="space-y-5">
                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-4">
                            <div className="flex items-center gap-3 text-sm">
                                <ShieldCheck className="h-5 w-5 text-emerald-300" />
                                <div>
                                    <p className="font-semibold text-zinc-100">Signed local session · {identity.subject}</p>
                                    <p className="text-xs text-zinc-400">Role: {identity.role} · Demo identity only · No real customer access</p>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <button onClick={refresh} disabled={busy} className="inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-xs text-zinc-300 hover:bg-white/10 disabled:opacity-50">
                                    <RefreshCw className="h-3.5 w-3.5" /> Refresh
                                </button>
                                <button onClick={disconnect} className="inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-xs text-zinc-300 hover:bg-white/10">
                                    <LogOut className="h-3.5 w-3.5" /> Disconnect
                                </button>
                            </div>
                        </div>

                        <div className="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
                            <div className="space-y-5">
                                <form onSubmit={openCase} className="space-y-4 rounded-3xl border border-white/10 bg-zinc-900/70 p-5">
                                    <div>
                                        <h2 className="text-lg font-semibold">Open a synthetic case</h2>
                                        <p className="mt-1 text-xs text-zinc-400">Requires an accepted, model-scored local transaction.</p>
                                    </div>
                                    <label className="block space-y-2 text-xs text-zinc-300">
                                        <span>Transaction ID</span>
                                        <input
                                            value={transactionId} onChange={(event) => setTransactionId(event.target.value)}
                                            placeholder="synthetic-transaction-id" maxLength={128} required
                                            className="w-full rounded-xl border border-zinc-700 bg-black/60 px-3 py-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-400"
                                        />
                                    </label>
                                    <button type="submit" disabled={busy || !transactionId.trim()} className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-200 px-4 py-3 text-sm font-semibold text-zinc-950 hover:bg-white disabled:opacity-50">
                                        <ClipboardList className="h-4 w-4" /> Create verified case
                                    </button>
                                </form>
                                <section className="rounded-3xl border border-white/10 bg-zinc-900/60 p-5" aria-label="Verified synthetic case queue">
                                    <div className="mb-4 flex items-center justify-between">
                                        <h2 className="text-lg font-semibold">Local case queue</h2>
                                        <span className="text-xs text-zinc-500">Up to 25 recent</span>
                                    </div>
                                    <div className="space-y-2">
                                        {cases.length === 0 && (
                                            <p className="rounded-xl border border-dashed border-zinc-700 p-4 text-sm text-zinc-500">
                                                No verified cases in this local ledger. Open one using an accepted synthetic transaction ID.
                                            </p>
                                        )}
                                        {cases.map((item) => (
                                            <button key={item.case_id} type="button" disabled={busy}
                                                onClick={() => selectCase(item.case_id)}
                                                aria-pressed={focus?.case_id === item.case_id}
                                                className={ "w-full rounded-xl border p-3 text-left transition disabled:opacity-60 " +
                                                    (focus?.case_id === item.case_id
                                                        ? "border-violet-400/60 bg-violet-400/10"
                                                        : "border-white/5 bg-black/30 hover:border-white/20") }>
                                                <span className="flex items-center justify-between gap-2">
                                                    <span className="truncate font-mono text-xs text-zinc-100">{shortenHash(item.case_id, 16)}</span>
                                                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                                                </span>
                                                <span className="mt-2 block text-xs text-zinc-400">{item.status.replace(/_/g, " ")}</span>
                                                <span className="mt-1 block truncate text-[11px] text-zinc-500">{item.transaction_id}</span>
                                            </button>
                                        ))}
                                    </div>
                                </section>
                            </div>

                            <div className="space-y-5">
                                {!focus && (
                                    <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-white/15 bg-zinc-900/35 p-8 text-center">
                                        <Activity className="h-7 w-7 text-violet-300" />
                                        <h2 className="text-xl font-semibold text-white">Select an investigation</h2>
                                        <p className="max-w-md text-sm text-zinc-400">Only case records returned by the signed local API appear here. No decorative customer events or synthetic model values are substituted.</p>
                                    </div>
                                )}
                                {focus && (
                                    <>
                                        <section className="rounded-3xl border border-white/10 bg-zinc-900/85 p-5 sm:p-7">
                                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-300">Verified case record</p>
                                            <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
                                                <div>
                                                    <h2 className="break-all font-mono text-xl font-semibold text-white">{focus.case_id}</h2>
                                                    <p className="mt-2 break-all text-sm text-zinc-400">Transaction: {focus.transaction_id}</p>
                                                </div>
                                                <span className="rounded-full border border-violet-300/25 bg-violet-300/10 px-3 py-1 text-xs font-semibold text-violet-200">{focus.status.replace(/_/g, " ")}</span>
                                            </div>
                                            <div className="mt-5 grid gap-3 sm:grid-cols-3">
                                                <div className="rounded-xl border border-white/5 bg-black/30 p-4">
                                                    <p className="text-xs text-zinc-400">Model output</p>
                                                    <p className="mt-2 text-2xl font-semibold text-white tabular-nums">{(focus.evidence.score * 100).toFixed(1)}%</p>
                                                    <p className="text-[11px] text-zinc-500">Uncalibrated, synthetic only</p>
                                                </div>
                                                <div className="rounded-xl border border-white/5 bg-black/30 p-4">
                                                    <p className="text-xs text-zinc-400">Review version</p>
                                                    <p className="mt-2 text-2xl font-semibold text-white tabular-nums">{focus.version}</p>
                                                    <p className="text-[11px] text-zinc-500">Optimistic write control</p>
                                                </div>
                                                <div className="rounded-xl border border-white/5 bg-black/30 p-4">
                                                    <p className="text-xs text-zinc-400">Audit events</p>
                                                    <p className="mt-2 text-2xl font-semibold text-white tabular-nums">{focus.events.length}</p>
                                                    <p className="text-[11px] text-zinc-500">Signed local event chain</p>
                                                </div>
                                            </div>
                                            <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
                                                <p className="mb-2 text-xs font-semibold text-zinc-200">Provenance · click hash for full value</p>
                                                <HashLine label="Source event" hash={focus.evidence.source_payload_sha256} />
                                                <HashLine label="PIT snapshot" hash={focus.evidence.feature_snapshot_sha256} />
                                                <HashLine label="Trained model" hash={focus.evidence.model_sha256} />
                                                <HashLine label="Native SHAP" hash={focus.evidence.explanation_sha256} />
                                                <HashLine label="Audit chain head" hash={focus.audit_head_sha256} />
                                            </div>
                                            <div className="mt-5">
                                                <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">Human-only review controls</p>
                                                {actions.length > 0 ? (
                                                    <div className="flex flex-wrap gap-2">
                                                        {actions.map((action) => (
                                                            <button key={action} type="button" disabled={busy}
                                                                onClick={() => submitAction(action)}
                                                                className="inline-flex items-center gap-2 rounded-full border border-violet-300/25 bg-violet-300/10 px-4 py-2.5 text-xs font-semibold text-violet-100 transition hover:bg-violet-300/20 disabled:opacity-50">
                                                                {readableAction[action]} <ArrowRight className="h-3.5 w-3.5" />
                                                            </button>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <p className="rounded-xl border border-white/10 bg-black/30 p-3 text-sm text-zinc-400">
                                                        No permitted action for this role and state. Closed cases remain closed.
                                                    </p>
                                                )}
                                                <p className="mt-3 text-xs text-amber-300">Review actions change case states only; they never decline payments or establish actual fraud.</p>
                                            </div>
                                        </section>
                                        {explanation && <VerifiedShapChart explanation={explanation} />}
                                        <section className="rounded-3xl border border-white/10 bg-zinc-900/70 p-5 sm:p-7" aria-label="Verified case audit timeline">
                                            <div className="mb-5 flex items-center gap-2">
                                                <ClipboardList className="h-5 w-5 text-violet-200" />
                                                <h2 className="text-xl font-semibold">Human-review audit timeline</h2>
                                            </div>
                                            <ol className="space-y-4">
                                                {focus.events.map((event) => (
                                                    <li key={event.sequence} className="relative border-l border-violet-300/20 pb-3 pl-5">
                                                        <span aria-hidden="true" className="absolute -left-1 top-1 h-2 w-2 rounded-full bg-violet-300" />
                                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                                            <p className="text-sm font-medium text-white">{event.action.replace(/_/g, " ")}</p>
                                                            <time className="text-xs text-zinc-500">{dateLabel(event.created_at_utc)}</time>
                                                        </div>
                                                        <p className="mt-1 text-xs text-zinc-400">Signed {event.reviewer_role}: {event.reviewer_id} · State: {event.state_after.replace(/_/g, " ")}</p>
                                                        <p className="mt-1 break-all font-mono text-[10px] text-zinc-600">Event #{event.sequence} · previous SHA-256 {shortenHash(event.previous_event_sha256, 16)}</p>
                                                    </li>
                                                ))}
                                            </ol>
                                            <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-zinc-500">
                                                <LockKeyhole className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                                                Events are checked against the local keyed hash chain. This is not an independently anchored or regulator-certified audit ledger.
                                            </p>
                                        </section>
                                    </>
                                )}
                            </div>
                        </div>
                    </section>
                )}
            </main>
            <Footer />
        </div>
    );
}
