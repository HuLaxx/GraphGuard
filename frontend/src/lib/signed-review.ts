/** Local synthetic-only review data types; never infer fraud outcomes. */
export type ReviewerRole = "analyst" | "admin";
export type ReviewState =
    | "OPEN" | "NEEDS_INFORMATION" | "ESCALATED"
    | "CLOSED_NO_ACTION" | "CLOSED_REVIEW_COMPLETE";
export type ReviewAction =
    | "request_more_information" | "escalate"
    | "close_no_action" | "close_review_complete";

export interface ReviewIdentity {
    subject: string;
    role: ReviewerRole;
    scope: "SYNTHETIC_LOCAL_REVIEW_ONLY";
}
export interface ReviewEvidence {
    transaction_id: string;
    score: number;
    manifest_sha256: string;
    model_sha256: string;
    source_payload_sha256: string;
    feature_snapshot_sha256: string;
    explanation_sha256: string;
    feature_version: string;
    model_input_version: string;
    explainer_version: string;
    scope: "SYNTHETIC_ONLY_HUMAN_REVIEW_DEMO";
}
export interface ReviewEvent {
    case_id: string;
    sequence: number;
    request_id: string;
    action: string;
    state_after: ReviewState;
    reviewer_id: string;
    reviewer_role: ReviewerRole;
    actor_token_jti: string;
    previous_event_sha256: string;
    created_at_utc: string;
    schema_version: string;
}
export interface ReviewCase {
    case_id: string;
    transaction_id: string;
    status: ReviewState;
    version: number;
    evidence: ReviewEvidence;
    audit_head_sha256: string;
    events: ReviewEvent[];
}
export interface ReviewFeature {
    feature: string;
    value: number;
    shap_log_odds: number;
    direction: string;
}
export interface ReviewExplanation {
    transaction_id: string;
    scope: "SYNTHETIC_ONLY_RESEARCH_EXPLANATION";
    status: string;
    non_causal_notice: string;
    method: string;
    background: string;
    attribution_scale: "raw_log_odds";
    reconstructed_probability: number;
    verified_model_probability: number;
    reconstruction_abs_error: number;
    base_log_odds: number;
    reconstructed_log_odds: number;
    all_features: ReviewFeature[];
    top_features: ReviewFeature[];
    model_sha256: string;
    manifest_sha256: string;
    source_payload_sha256: string;
    feature_snapshot_sha256: string;
    explanation_sha256: string;
}

export const readableAction: Record<ReviewAction, string> = {
    request_more_information: "Request information",
    escalate: "Escalate for review",
    close_no_action: "Close — no action",
    close_review_complete: "Close — review complete",
};

export function allowedReviewActions(state: ReviewState, role: ReviewerRole): ReviewAction[] {
    if (state === "OPEN") {
        return role === "admin"
            ? ["request_more_information", "escalate", "close_no_action"]
            : ["request_more_information", "escalate"];
    }
    if (state === "NEEDS_INFORMATION") {
        return role === "admin" ? ["escalate", "close_no_action"] : ["escalate"];
    }
    if (state === "ESCALATED" && role === "admin") {
        return ["close_no_action", "close_review_complete"];
    }
    return [];
}

export function shortenHash(value: string, visible = 11): string {
    return value.length >= 32 ? value.slice(0, visible) + "…" : value;
}

export async function fetchSignedReview<T>(
    path: string,
    token: string,
    options: { method?: "GET" | "POST"; body?: Record<string, unknown> } = {},
): Promise<T> {
    // Token stays in React component memory; never persisted, logged or
    // appended to a URL, cookie or browser localStorage.
    const result = await fetch("/review-local/" + path, {
        method: options.method ?? "GET",
        headers: {
            Authorization: "Bearer " + token,
            ...(options.body ? { "Content-Type": "application/json" } : {}),
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        cache: "no-store",
    });
    let json: unknown;
    try {
        json = await result.json();
    } catch {
        throw new Error("Invalid response from the local review bridge.");
    }
    if (!result.ok) {
        const detail =
            json && typeof json === "object" && "detail" in json
                ? String(json.detail) : "Review request failed";
        throw new Error(result.status + ": " + detail);
    }
    return json as T;
}
