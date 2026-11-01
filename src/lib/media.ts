type Loose = Record<string, unknown>;

function pushUrl(urls: string[], value: unknown): void {
  if (!value) return;
  if (typeof value === "string") {
    urls.push(value);
    return;
  }
  if (Array.isArray(value)) {
    for (const entry of value) pushUrl(urls, entry);
    return;
  }
  if (typeof value === "object") {
    const record = value as Loose;
    if (typeof record.url === "string") urls.push(record.url);
    if (typeof record.href === "string") urls.push(record.href);
    const attrs = record.$;
    if (attrs && typeof attrs === "object") {
      const url = (attrs as Loose).url;
      if (typeof url === "string") urls.push(url);
    }
  }
}

function looksLikeImage(url: string): boolean {
  return /\.(jpe?g|png|webp|gif|avif)(\?|$)/i.test(url) || /\/(image|images|img|photos|media)\//i.test(url);
}

export function pickImage(item: Loose): string | undefined {
  const urls: string[] = [];
  pushUrl(urls, item.enclosure);
  pushUrl(urls, item.enclosures);
  pushUrl(urls, item.mediaThumbnail);
  pushUrl(urls, item.mediaContent);
  pushUrl(urls, item["media:thumbnail"]);
  pushUrl(urls, item["media:content"]);

  for (const url of urls) {
    const clean = url.trim().replace(/&amp;/g, "&");
    if (!/^https?:\/\//i.test(clean)) continue;
    if (looksLikeImage(clean)) return clean;
  }

  const enclosure = item.enclosure;
  if (enclosure && typeof enclosure === "object") {
    const record = enclosure as Loose;
    const type = typeof record.type === "string" ? record.type : "";
    const url = typeof record.url === "string" ? record.url.trim() : "";
    if (type.startsWith("image/") && /^https?:\/\//i.test(url)) return url;
  }

  return undefined;
}
