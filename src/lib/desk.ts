export type ArticleDeskStatus = "DRAFT" | "PUBLISHED" | "DELETED";

/** A fresh RSS item becomes a draft. Published and deleted rows stay as the editor left them. */
export function incomingStatus(current: ArticleDeskStatus | null): "create" | "refresh" | "leave" {
  if (current === null) return "create";
  if (current === "DRAFT") return "refresh";
  return "leave";
}

export function parseSourceName(value: string): string | null {
  const name = value.trim().replace(/\s+/g, " ").slice(0, 80);
  if (name.length < 2) return null;
  return name;
}

export function parseFeedUrl(value: string): string | null {
  const raw = value.trim();
  if (!raw || raw.length > 500) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.toString();
  } catch {
    return null;
  }
}
