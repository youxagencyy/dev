import type { ArticleCategory, Source } from "@prisma/client";
import { loadFeed } from "./aggregate";
import { categoryFromEnum, categoryToEnum } from "./categories";
import { incomingStatus } from "./desk";
import { requirePrisma } from "./db";
import type { FeedFailure, NewsItem } from "./types";

export type IngestResult = {
  created: number;
  refreshed: number;
  failures: FeedFailure[];
};

function articleData(item: NewsItem, source: Source) {
  const publishedAt = Number.isNaN(Date.parse(item.publishedAt)) ? null : new Date(item.publishedAt);
  return {
    title: item.title,
    summaryBullets: item.summary ? [item.summary] : [],
    tags: item.tags,
    coverUrl: item.image ?? null,
    category: categoryToEnum(item.category) as ArticleCategory,
    outletName: source.name,
    publishedAt,
    sourceId: source.id,
  };
}

async function storeItems(source: Source, items: NewsItem[]): Promise<Pick<IngestResult, "created" | "refreshed">> {
  const prisma = requirePrisma();
  let created = 0;
  let refreshed = 0;
  for (const item of items) {
    const existing = await prisma.article.findUnique({
      where: { slug: item.id },
      select: { status: true },
    });
    const decision = incomingStatus(existing?.status ?? null);
    if (decision === "leave") continue;
    const data = articleData(item, source);
    if (decision === "refresh") {
      await prisma.article.update({ where: { slug: item.id }, data });
      refreshed += 1;
      continue;
    }
    try {
      await prisma.article.create({
        data: { slug: item.id, rewrittenBody: "", status: "DRAFT", ...data },
      });
      created += 1;
    } catch (error) {
      const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
      if (code !== "P2002") throw error;
    }
  }
  return { created, refreshed };
}

export async function ingestSource(id: string): Promise<IngestResult> {
  const prisma = requirePrisma();
  const source = await prisma.source.findUnique({ where: { id } });
  if (!source || !source.active) return { created: 0, refreshed: 0, failures: [] };
  const fallback = categoryFromEnum(source.fallback) ?? "ukraina";
  const loaded = await loadFeed({ name: source.name, url: source.feedUrl, fallback });
  if (loaded.failure) return { created: 0, refreshed: 0, failures: [loaded.failure] };
  const stored = await storeItems(source, loaded.items);
  return { ...stored, failures: [] };
}

export async function ingestEnabledSources(): Promise<IngestResult> {
  const prisma = requirePrisma();
  const sources = await prisma.source.findMany({ where: { active: true }, orderBy: { name: "asc" } });
  const results = await Promise.all(sources.map((source) => ingestSource(source.id)));
  return {
    created: results.reduce((sum, result) => sum + result.created, 0),
    refreshed: results.reduce((sum, result) => sum + result.refreshed, 0),
    failures: results.flatMap((result) => result.failures),
  };
}
