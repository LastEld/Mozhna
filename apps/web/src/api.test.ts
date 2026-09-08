import { describe, it, expect } from "vitest";
import { cents, euros, money } from "./api";

describe("exact EUR display and input", () => {
  it.each([
    ["0.01", 1],
    ["1,50", 150],
    ["-0.50", -50],
    ["90071992547409.91", Number.MAX_SAFE_INTEGER],
  ])("round-trips %s without floating point cents", (input, minor) => {
    expect(cents(input)).toBe(minor);
    expect(cents(euros(minor))).toBe(minor);
  });
  it.each(["1.005", "1e3", "NaN", "90071992547409.92", ""])(
    "rejects %s",
    (value) => {
      expect(() => cents(value)).toThrow();
    },
  );
  it("does not show unsafe or absent totals as money", () => {
    expect(money(null)).toBe("—");
    expect(money(Number.MAX_SAFE_INTEGER + 1)).toBe("—");
    expect(money(Number.MAX_SAFE_INTEGER)).toContain(",91");
    expect(money(-50)).toContain("-0,50");
  });
});
