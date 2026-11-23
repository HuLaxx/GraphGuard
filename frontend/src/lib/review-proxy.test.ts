import { describe, expect, it } from "vitest";
import { localReviewPath } from "./review-proxy";

const valid = "gg-" + "a".repeat(24);

describe("local synthetic review route allowlist", () => {
    it("allows only documented signed review operations", () => {
        expect(localReviewPath(["session"], "GET")).toBe("session");
        expect(localReviewPath(["cases"], "GET")).toBe("cases");
        expect(localReviewPath(["cases"], "POST")).toBe("cases");
        expect(localReviewPath(["cases", valid], "GET")).toBe("cases/" + valid);
        expect(localReviewPath(["cases", valid, "explanation"], "GET")).toBe(
            "cases/" + valid + "/explanation"
        );
        expect(localReviewPath(["cases", valid, "actions"], "POST")).toBe(
            "cases/" + valid + "/actions"
        );
    });
    it("blocks traversal, unsupported actions and arbitrary forwarding", () => {
        expect(localReviewPath([], "GET")).toBeNull();
        expect(localReviewPath(["health"], "GET")).toBeNull();
        expect(localReviewPath(["cases", "anything"], "GET")).toBeNull();
        expect(localReviewPath(["cases", valid, "actions"], "GET")).toBeNull();
        expect(localReviewPath(["cases", valid, "explanation"], "POST")).toBeNull();
        expect(localReviewPath(["..", "admin"], "POST")).toBeNull();
        expect(localReviewPath(["http:", "example.com"], "GET")).toBeNull();
        expect(localReviewPath(["cases", valid, "unexpected"], "POST")).toBeNull();
        expect(localReviewPath(["cases"], "DELETE")).toBeNull();
        expect(localReviewPath(["session"], "POST")).toBeNull();
    });
});
