import { localReviewPath } from "@/lib/review-proxy";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type ReviewContext = { params: Promise<{ path?: string[] }> };

async function forward(request: Request, context: ReviewContext): Promise<Response> {
    // This browser bridge is strictly a local development demo. Do not
    // expose signed review bearer tokens through a hosted Next.js server.
    if (process.env.NODE_ENV !== "development") {
        return Response.json(
            { detail: "Signed review bridge is available only in local development mode." },
            { status: 404, headers: { "Cache-Control": "no-store" } },
        );
    }
    const { path } = await context.params;
    const permitted = localReviewPath(path, request.method);
    if (!permitted) {
        return Response.json(
            { detail: "Unsupported review operation" },
            { status: 404, headers: { "Cache-Control": "no-store" } },
        );
    }
    const authorization = request.headers.get("authorization");
    if (!authorization || !/^Bearer [A-Za-z0-9_.-]{16,2048}$/.test(authorization)) {
        return Response.json(
            { detail: "A signed local demo reviewer token is required" },
            { status: 401, headers: { "Cache-Control": "no-store" } },
        );
    }
    let body: string | undefined;
    if (request.method === "POST") {
        if (!request.headers.get("content-type")?.startsWith("application/json")) {
            return Response.json({ detail: "JSON body required" }, { status: 415 });
        }
        body = await request.text();
        if (body.length > 4096) {
            return Response.json({ detail: "Review request too large" }, { status: 413 });
        }
        try {
            const parsed: unknown = JSON.parse(body);
            if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
                return Response.json({ detail: "Review JSON object required" }, { status: 400 });
            }
        } catch {
            return Response.json({ detail: "Invalid JSON" }, { status: 400 });
        }
    }
    try {
        const upstream = await fetch("http://127.0.0.1:8765/" + permitted, {
            method: request.method,
            headers: {
                Authorization: authorization,
                ...(body === undefined ? {} : { "Content-Type": "application/json" }),
            },
            body,
            cache: "no-store",
            redirect: "error",
            signal: AbortSignal.timeout(10000),
        });
        const text = await upstream.text();
        if (text.length > 131072) {
            return Response.json({ detail: "Local review response too large" }, { status: 502 });
        }
        let data: unknown;
        try {
            data = JSON.parse(text);
        } catch {
            return Response.json({ detail: "Invalid local review response" }, { status: 502 });
        }
        return Response.json(data, {
            status: upstream.status,
            headers: { "Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff" },
        });
    } catch {
        return Response.json(
            { detail: "Local signed review API unavailable on 127.0.0.1:8765." },
            { status: 503, headers: { "Cache-Control": "no-store" } },
        );
    }
}

export async function GET(request: Request, context: ReviewContext) {
    return forward(request, context);
}

export async function POST(request: Request, context: ReviewContext) {
    return forward(request, context);
}
