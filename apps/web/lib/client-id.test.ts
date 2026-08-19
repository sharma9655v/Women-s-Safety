import { beforeEach, describe, expect, it } from "vitest";
import { clientId } from "./client-id";

describe("clientId", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("generates a 64-char lowercase hex id", () => {
    const id = clientId();
    expect(id).toMatch(/^[0-9a-f]{64}$/);
  });

  it("persists the generated id for reuse", () => {
    const first = clientId();
    const second = clientId();
    expect(second).toBe(first);
    expect(localStorage.getItem("mf:client_id")).toBe(first);
  });

  it("regenerates when the stored value is invalid", () => {
    localStorage.setItem("mf:client_id", "not-a-valid-id");
    expect(clientId()).toMatch(/^[0-9a-f]{64}$/);
  });
});
