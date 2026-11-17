/**
 * Explicit local-only proxy allowlist.
 * No generic path forwarding and no user-controlled upstream host.
 */
const CASE_ID = /^gg-[a-f0-9]{24}$/;

export function localReviewPath(parts: string[] | undefined, method: string): string | null {
    if (!parts || parts.length === 0) return null;
    if (parts.length === 1 && parts[0] === "session" && method === "GET") return "session";
    if (parts.length === 1 && parts[0] === "cases" && ["GET", "POST"].includes(method)) return "cases";
    if (parts.length === 2 && parts[0] === "cases" && CASE_ID.test(parts[1]) && method === "GET") {
        return "cases/" + parts[1];
    }
    if (parts.length === 3 && parts[0] === "cases" && CASE_ID.test(parts[1])) {
        if (parts[2] === "explanation" && method === "GET") {
            return "cases/" + parts[1] + "/explanation";
        }
        if (parts[2] === "actions" && method === "POST") {
            return "cases/" + parts[1] + "/actions";
        }
    }
    return null;
}
