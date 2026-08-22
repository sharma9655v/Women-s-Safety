/**
 * Pseudonymous device identity.
 *
 * Every personal-safety API call carries an X-Client-Id: a device-generated
 * random hex string (32-64 chars) stored only in this browser. It is NOT a
 * name, email or phone; the backend stores only a hash of it and never links
 * it to an account. Clearing browser data resets the identity.
 */

const KEY = "mf:client_id";
const HEX = /^[0-9a-f]{32,64}$/;

export function clientId(): string {
  let value = "";
  try {
    value = localStorage.getItem(KEY) ?? "";
  } catch {
    // localStorage unavailable (private mode, SSR) -> generate per-session id
  }
  if (!HEX.test(value)) {
    value = generate();
    try {
      localStorage.setItem(KEY, value);
    } catch {
      // keep the in-memory value; identity lasts for this tab only
    }
  }
  return value;
}

function generate(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
