import { beforeEach, describe, expect, it } from "vitest";
import { getAdminKey, setAdminKey } from "./admin-key";

describe("admin key storage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns an empty key when nothing is stored", () => {
    expect(getAdminKey()).toBe("");
  });

  it("stores and reads the key in sessionStorage only", () => {
    setAdminKey("s3cret");
    expect(getAdminKey()).toBe("s3cret");
    expect(sessionStorage.getItem("safety-admin-key")).toBe("s3cret");
    expect(localStorage.getItem("safety-admin-key")).toBeNull();
  });

  it("round-trips an empty value", () => {
    setAdminKey("");
    expect(getAdminKey()).toBe("");
  });
});
