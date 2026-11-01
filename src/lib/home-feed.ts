import type { CategorySlug } from "./categories";
import type { NewsItem } from "./types";

const BRIEF_ORDER: CategorySlug[] = ["viina", "ukraina", "polityka", "svit"];

export function pickBrief(items: NewsItem[], count = 5): NewsItem[] {
  const picked: NewsItem[] = [];
  const seen = new Set<string>();

  for (const category of BRIEF_ORDER) {
    const found = items.find((item) => item.category === category);
    if (!found || seen.has(found.id)) continue;
    picked.push(found);
    seen.add(found.id);
  }

  for (const item of items) {
    if (picked.length >= count) break;
    if (seen.has(item.id)) continue;
    picked.push(item);
    seen.add(item.id);
  }

  return picked
    .sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt))
    .slice(0, count);
}

export function laneItems(
  items: NewsItem[],
  category: CategorySlug,
  exclude: Set<string>,
  count = 4,
): NewsItem[] {
  const all = items.filter((item) => item.category === category);
  const fresh = all.filter((item) => !exclude.has(item.id));
  return (fresh.length >= 3 ? fresh : all).slice(0, count);
}
