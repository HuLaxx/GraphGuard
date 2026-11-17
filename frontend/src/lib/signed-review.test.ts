import { describe, expect, it } from "vitest";
import { allowedReviewActions, shortenHash } from "./signed-review";

describe("verified local case-action affordances", () => {
    it("prevents analysts from closing and forbids all actions after closure", () => {
        expect(allowedReviewActions("OPEN", "analyst")).toEqual([
            "request_more_information", "escalate",
        ]);
        expect(allowedReviewActions("ESCALATED", "analyst")).toEqual([]);
        expect(allowedReviewActions("ESCALATED", "admin")).toEqual([
            "close_no_action", "close_review_complete",
        ]);
        expect(allowedReviewActions("CLOSED_NO_ACTION", "admin")).toEqual([]);
        expect(allowedReviewActions("CLOSED_REVIEW_COMPLETE", "analyst")).toEqual([]);
    });
    it("only truncates long hashes for visual presentation", () => {
        expect(shortenHash("abcd")).toBe("abcd");
        expect(shortenHash("a".repeat(64))).toBe("a".repeat(11) + "…");
    });
});
