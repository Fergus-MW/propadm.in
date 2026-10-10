import { describe, expect, it } from "vitest";
import { exampleTestCase, parseTestCases } from "../lib/workflow-tuning";

describe("private next-step cases", () => {
  it("loads a nine-step case with its reference separated from the history", () => {
    const cases = parseTestCases(JSON.stringify(exampleTestCase));
    expect(cases[0].steps).toHaveLength(9);
    expect(cases[0].steps).not.toContain(cases[0].expected);
    expect(parseTestCases(JSON.stringify([exampleTestCase, exampleTestCase]))).toHaveLength(2);
  });
  it("accepts prediction-only cases and rejects empty or malformed histories", () => {
    expect(parseTestCases('{"name":"Test","steps":["First step"]}')[0].expected).toBe("");
    for (const value of [[], {}, { name: "Test", steps: [] }, { name: "Test", steps: [""] },
      { name: "Test", steps: [42] }, { ...exampleTestCase, future_answer: "Leak" }])
      expect(() => parseTestCases(JSON.stringify(value))).toThrow();
  });
});
