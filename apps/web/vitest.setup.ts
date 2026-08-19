/// <reference types="vitest/globals" />
import "@testing-library/jest-dom/vitest";

// jsdom lacks crypto.randomUUID in some environments; provide a stable one.
if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis.crypto, "randomUUID", {
    value: () => "00000000-0000-4000-8000-000000000000",
  });
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
