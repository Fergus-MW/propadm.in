export type PrivateTestCase = {
  name: string;
  initial_context: string;
  steps: string[];
  expected: string;
};

export function parseTestCases(text: string): PrivateTestCase[] {
  const parsed: unknown = JSON.parse(text);
  const cases = Array.isArray(parsed) ? parsed : [parsed];
  if (!cases.length || cases.length > 20) throw new Error("Load between 1 and 20 cases.");
  return cases.map((value, index) => {
    if (!value || typeof value !== "object" || Array.isArray(value))
      throw new Error(`Case ${index + 1} must be an object.`);
    const item = value as Record<string, unknown>;
    if (Object.keys(item).some((key) => !["name", "initial_context", "steps", "expected"].includes(key)))
      throw new Error(`Case ${index + 1} has an unknown field.`);
    if (typeof item.name !== "string" || !item.name.trim() || item.name.length > 200)
      throw new Error(`Case ${index + 1} needs a name.`);
    if (!Array.isArray(item.steps) || !item.steps.length || item.steps.length > 500 ||
      item.steps.some((step) => typeof step !== "string" || !step.trim() || step.length > 30000) ||
      item.steps.reduce((total, step: string) => total + step.length, 0) > 150000)
      throw new Error(`Case ${index + 1} needs nonempty ordered steps (up to 150,000 characters).`);
    if (item.initial_context !== undefined && (typeof item.initial_context !== "string" || item.initial_context.length > 20000))
      throw new Error(`Case ${index + 1} has invalid initial context.`);
    if (item.expected !== undefined && (typeof item.expected !== "string" || item.expected.length > 30000))
      throw new Error(`Case ${index + 1} has an invalid reference step.`);
    return { name: item.name, steps: item.steps as string[],
      initial_context: (item.initial_context as string | undefined) ?? "",
      expected: (item.expected as string | undefined) ?? "" };
  });
}

export const exampleTestCase: PrivateTestCase = {
  name: "Unseen maintenance case",
  initial_context: "Tenant reports a leaking kitchen tap.",
  steps: [
    "Tenant emails the agency to report the leak.",
    "Agency asks for a photo and whether the stopcock works.",
    "Tenant sends a photo and confirms the water can be isolated.",
    "Agency checks the landlord's spending limit.",
    "Agency requests quotes and attendance times from qualified plumbers.",
    "Plumber A quotes £120 and offers Tuesday morning.",
    "Plumber B quotes £150 and offers Thursday afternoon.",
    "Agency obtains the landlord's approval for Plumber A's quote.",
    "Landlord approves the £120 quote and Tuesday morning appointment.",
  ],
  expected: "Book Plumber A within the approved quote and confirm access with the tenant.",
};
