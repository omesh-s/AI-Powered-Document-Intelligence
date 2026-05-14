import { describe, expect, it } from "vitest";

import { ApiError, formatApiError } from "./apiClient";

describe("formatApiError", () => {
  it("formats AppError envelope", () => {
    const e = new ApiError(400, { error: { code: "BAD", message: "Nope" } });
    expect(formatApiError(e)).toBe("BAD: Nope");
  });

  it("formats string body from storage PUT", () => {
    const e = new ApiError(403, "<?xml...");
    expect(formatApiError(e)).toContain("<?xml");
  });
});
