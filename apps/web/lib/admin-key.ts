const ADMIN_KEY_STORAGE = "safety-admin-key";

/** Read the admin key. Kept in sessionStorage (per-tab, cleared on close)
 * rather than localStorage so the credential does not persist indefinitely
 * in the browser. */
export function getAdminKey(): string {
  try {
    return window.sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function setAdminKey(key: string): void {
  try {
    window.sessionStorage.setItem(ADMIN_KEY_STORAGE, key);
  } catch {
    // storage unavailable — the key stays in memory for this session
  }
}
