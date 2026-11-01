import Parser from "rss-parser";
import { unstable_cache } from "next/cache";
import { FEEDS, type FeedSource } from "./feeds";
import { pickImage } from "./media";
import { classify, dedupe, isFresh, isOffTopic, makeId, normalizeTitle, toExcerpt } from "./text";
import type { FeedFailure, NewsItem, NewsSnapshot } from "./types";

const PER_FEED_LIMIT = 25;
const REQUEST_TIMEOUT_MS = 12_000;

const parser = new Parser({
  timeout: REQUEST_TIMEOUT_MS,
  customFields: {
    item: [
      ["media:thumbnail", "mediaThumbnail"],
      ["media:content", "mediaContent", { keepArray: true }],
    ],
  },
});

type ParsedItem = {
  title?: string;
  contentSnippet?: string;
  summary?: string;
  content?: string;
  isoDate?: string;
  pubDate?: string;
  categories?: string[];
  enclosure?: { url?: string; type?: string };
};

async function loadFeed(feed: FeedSource): Promise<{ items: NewsItem[]; failure?: FeedFailure }> {
  try {
    const response = await fetch(feed.url, {
      headers: {
        Accept: "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "uk",
        "User-Agent": "Varta/0.1 (public news digest; headlines and short excerpts)",
      },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });

    if (!response.ok) {
      return { items: [], failure: { source: feed.name, reason: `HTTP ${response.status}` } };
    }

    const xml = await response.text();
    const parsed = await parser.parseString(xml);
    const rawItems = (parsed.items ?? []) as ParsedItem[];
    const items: NewsItem[] = [];

    for (const raw of rawItems) {
      if (items.length >= PER_FEED_LIMIT) break;
      const title = toExcerpt(raw.title, 240).replace(/…$/, "");
      if (!title) continue;

      const categories = Array.isArray(raw.categories)
        ? raw.categories.filter((category): category is string => typeof category === "string")
        : [];
      if (isOffTopic(title, categories)) continue;

      const publishedAt = raw.isoDate || raw.pubDate || "";
      const parsedDate = Date.parse(publishedAt);
      if (Number.isNaN(parsedDate) || !isFresh(new Date(parsedDate).toISOString())) continue;

      const described = raw as ParsedItem & {
        description?: string;
        "content:encodedSnippet"?: string;
      };
      // RSS description lands in contentSnippet. Full content:encoded bodies are only a last resort and are truncated.
      const summarySource =
        described.contentSnippet ||
        described.summary ||
        described.description ||
        described["content:encodedSnippet"] ||
        "";
      let summary = toExcerpt(summarySource, 320);
      if (summary && normalizeTitle(summary) === normalizeTitle(title)) summary = "";

      const image = pickImage(raw as unknown as Record<string, unknown>);
      items.push({
        id: makeId(title),
        title,
        summary,
        source: feed.name,
        publishedAt: new Date(parsedDate).toISOString(),
        category: classify(title, summary, categories, feed.fallback),
        ...(image ? { image } : {}),
      });
    }

    return { items };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "невідома помилка";
    return { items: [], failure: { source: feed.name, reason: reason.slice(0, 180) } };
  }
}

export async function loadNews(): Promise<NewsSnapshot> {
  const results = await Promise.all(FEEDS.map((feed) => loadFeed(feed)));
  const failures = results.flatMap((result) => (result.failure ? [result.failure] : []));
  const items = dedupe(results.flatMap((result) => result.items));
  const present = new Set(items.map((item) => item.source));

  for (const failure of failures) {
    console.warn(`[varta] пропущено «${failure.source}»: ${failure.reason}`);
  }

  return {
    items,
    fetchedAt: new Date().toISOString(),
    failures,
    sources: FEEDS.map((feed) => feed.name).filter((name) => present.has(name)),
  };
}

export const getNews = unstable_cache(loadNews, ["varta-news-v3"], { revalidate: 600 });
