import { describe, it, expect } from "vitest";
import { formatCurrency, formatNumber, formatPercent, getFraudScoreColor } from "./utils";

describe("utils", () => {
  it("formats currency", () => {
    expect(formatCurrency(100)).toContain("$");
  });

  it("formats numbers", () => {
    expect(formatNumber(1200)).toBe("1.2K");
    expect(formatNumber(2_000_000)).toBe("2.0M");
  });

  it("formats percent", () => {
    expect(formatPercent(0.1234, 1)).toBe("12.3%");
  });

  it("maps fraud score color", () => {
    expect(getFraudScoreColor(0.9)).toBe("text-red-400");
    expect(getFraudScoreColor(0.2)).toBe("text-emerald-400");
  });
});
