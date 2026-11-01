import type { CategorySlug } from "./categories";
import type { NewsItem } from "./types";

const CATEGORY_SLUGS: readonly CategorySlug[] = ["ukraina", "viina", "polityka", "svit"];

function fold(value: string): string {
  return value
    .toLocaleLowerCase("uk")
    .replace(/[’'`´ʼ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function categorySlug(value: string): CategorySlug | null {
  return CATEGORY_SLUGS.find((slug) => slug === value) ?? null;
}

export const TIME_WINDOWS = [
  { id: "all", label: "Увесь час" },
  { id: "today", label: "Сьогодні" },
  { id: "day", label: "24 години" },
  { id: "three", label: "3 дні" },
  { id: "week", label: "Тиждень" },
] as const;

export type TimeWindow = (typeof TIME_WINDOWS)[number]["id"];

export type SearchFilters = {
  query: string;
  category: CategorySlug | "all";
  tag: string;
  time: TimeWindow;
};

const KYIV = "Europe/Kyiv";

function kyivDay(ms: number): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: KYIV,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(ms);
}

export function queryTokens(query: string): string[] {
  return fold(query).split(" ").filter((token) => token.length > 0);
}

export function withinTime(iso: string, window: TimeWindow, now = Date.now()): boolean {
  if (window === "all") return true;
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return false;
  if (time > now + 60_000) return false;
  if (window === "today") return kyivDay(time) === kyivDay(now);
  const hours = window === "day" ? 24 : window === "three" ? 72 : 24 * 7;
  return now - time <= hours * 3_600_000;
}

const STEM_PAIRS = [
  ["київ", "києв"],
  ["харків", "харков"],
  ["львів", "львов"],
] as const;

function matchStems(token: string): string[] {
  const stems = new Set<string>([token]);
  const withoutVowels = token.replace(/[аеєиіїоуюяь]+$/u, "");
  if (withoutVowels.length >= 4 && withoutVowels !== token) stems.add(withoutVowels);
  for (const pair of STEM_PAIRS) {
    if (pair.some((stem) => token.startsWith(stem))) pair.forEach((stem) => stems.add(stem));
  }
  return [...stems].sort((left, right) => right.length - left.length);
}

export function matchesQuery(item: NewsItem, query: string): boolean {
  const tokens = queryTokens(query);
  if (tokens.length === 0) return true;
  const haystack = fold(`${item.title} ${item.summary} ${item.source} ${item.tags.join(" ")}`);
  return tokens.every((token) => matchStems(token).some((stem) => haystack.includes(stem)));
}

export function filterStories(items: NewsItem[], filters: SearchFilters, now = Date.now()): NewsItem[] {
  return items.filter((item) => {
    if (filters.category !== "all" && item.category !== filters.category) return false;
    if (filters.tag && !item.tags.includes(filters.tag)) return false;
    if (!withinTime(item.publishedAt, filters.time, now)) return false;
    return matchesQuery(item, filters.query);
  });
}

export type HighlightPart = { text: string; hit: boolean };

function foldedMap(text: string): { folded: string; toOriginal: number[] } | null {
  const lower = text.toLocaleLowerCase("uk");
  if (lower.length !== text.length) return null;
  let folded = "";
  const toOriginal: number[] = [];
  let lastWasSpace = true;
  for (let index = 0; index < lower.length; index += 1) {
    const char = lower[index] ?? "";
    if (/[’'`´ʼ]/.test(char)) continue;
    if (/\s/.test(char)) {
      if (lastWasSpace) continue;
      folded += " ";
      toOriginal.push(index);
      lastWasSpace = true;
      continue;
    }
    folded += char;
    toOriginal.push(index);
    lastWasSpace = false;
  }
  if (folded.endsWith(" ")) {
    folded = folded.slice(0, -1);
    toOriginal.pop();
  }
  return { folded, toOriginal };
}

function expandWord(folded: string, start: number, end: number): [number, number] {
  let from = start;
  let to = end;
  while (from > 0 && /[\p{L}\p{N}]/u.test(folded[from - 1] ?? "")) from -= 1;
  while (to < folded.length && /[\p{L}\p{N}]/u.test(folded[to] ?? "")) to += 1;
  return [from, to];
}

export function highlightParts(text: string, query: string): HighlightPart[] {
  if (!text) return [];
  const tokens = [...new Set(queryTokens(query))].sort((left, right) => right.length - left.length);
  if (tokens.length === 0) return [{ text, hit: false }];

  const mapped = foldedMap(text);
  if (!mapped) return [{ text, hit: false }];

  const ranges: [number, number][] = [];
  for (const token of tokens) {
    for (const stem of matchStems(token)) {
      let from = 0;
      while (from < mapped.folded.length) {
        const at = mapped.folded.indexOf(stem, from);
        if (at === -1) break;
        const [wordStart, wordEnd] = expandWord(mapped.folded, at, at + stem.length);
        const originalStart = mapped.toOriginal[wordStart];
        const originalEndIndex = mapped.toOriginal[wordEnd - 1];
        if (originalStart !== undefined && originalEndIndex !== undefined) {
          ranges.push([originalStart, originalEndIndex + 1]);
        }
        from = Math.max(wordEnd, at + stem.length);
      }
    }
  }

  if (ranges.length === 0) return [{ text, hit: false }];
  ranges.sort((left, right) => left[0] - right[0] || right[1] - left[1]);
  const merged: [number, number][] = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (!last || range[0] > last[1]) merged.push([range[0], range[1]]);
    else last[1] = Math.max(last[1], range[1]);
  }

  const parts: HighlightPart[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (start > cursor) parts.push({ text: text.slice(cursor, start), hit: false });
    parts.push({ text: text.slice(start, end), hit: true });
    cursor = end;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), hit: false });
  return parts.filter((part) => part.text.length > 0);
}

export function popularTags(items: NewsItem[], limit = 12): string[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    for (const tag of item.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "uk"))
    .slice(0, limit)
    .map(([tag]) => tag);
}

export function relatedStories(current: NewsItem, items: NewsItem[], limit = 3): NewsItem[] {
  const others = items.filter((item) => item.id !== current.id);
  const ranked = others
    .map((item) => {
      const shared = item.tags.filter((tag) => current.tags.includes(tag)).length;
      const sameCategory = item.category === current.category ? 3 : 0;
      return { item, score: sameCategory + shared * 2 };
    })
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return Date.parse(right.item.publishedAt) - Date.parse(left.item.publishedAt);
    });

  const picked = ranked.filter((entry) => entry.score > 0).slice(0, limit).map((entry) => entry.item);
  if (picked.length >= limit) return picked;

  const seen = new Set(picked.map((item) => item.id));
  const rest = [...others]
    .filter((item) => !seen.has(item.id))
    .sort((left, right) => Date.parse(right.publishedAt) - Date.parse(left.publishedAt));
  return [...picked, ...rest].slice(0, limit);
}

export function parseSearchFilters(input: {
  q?: string;
  category?: string;
  tag?: string;
  time?: string;
}): SearchFilters {
  const category = categorySlug(input.category ?? "") ?? "all";
  const time = TIME_WINDOWS.some((window) => window.id === input.time)
    ? (input.time as TimeWindow)
    : "all";
  return {
    query: (input.q ?? "").replace(/\s+/g, " ").trim().slice(0, 120),
    category,
    tag: (input.tag ?? "").trim().slice(0, 40),
    time,
  };
}

export function searchHref(filters: SearchFilters): string {
  const params = new URLSearchParams();
  if (filters.query) params.set("q", filters.query);
  if (filters.category !== "all") params.set("category", filters.category);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.time !== "all") params.set("time", filters.time);
  const query = params.toString();
  return query ? `/search?${query}` : "/search";
}
