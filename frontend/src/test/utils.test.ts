import { describe, it, expect } from "vitest";
import { cn, relativeTime } from "@/lib/utils";

describe("cn", () => {
  it("merges and dedupes tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });
});

describe("relativeTime", () => {
  it("returns 'just now' for current time", () => {
    expect(relativeTime(new Date().toISOString())).toBe("just now");
  });
  it("returns empty string for missing input", () => {
    expect(relativeTime(undefined)).toBe("");
  });
});
