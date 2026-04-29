// Browser-side glue for the optional Anthropic API key. The key is only
// ever sent to the orchestrator on localhost (the orchestrator refuses
// the field with 403 from any other origin). We persist it in
// sessionStorage so the user only types it once per tab and so it dies
// when the tab is closed.

const STORAGE_KEY = "hacksim:anthropic-key";

export function getAnthropicKey(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setAnthropicKey(value: string): void {
  if (typeof window === "undefined") return;
  try {
    if (value) window.sessionStorage.setItem(STORAGE_KEY, value);
    else window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // sessionStorage can throw in private mode; the key just won't persist.
  }
}

export function isLocalhostOrigin(): boolean {
  if (typeof window === "undefined") return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" || h === "::1" || h === "[::1]";
}
