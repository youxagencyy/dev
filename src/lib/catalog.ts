import { articleToItem } from "./articles";
import { getPrisma } from "./db";
import type { NewsSnapshot } from "./types";

const PUBLIC_LIMIT = 180;

function emptySnapshot(): NewsSnapshot {
  return { items: [], fetchedAt: new Date().toISOString(), failures: [], sources: [] };
}

/** Published stories only. A failed ingest does not remove these rows. */
export async function getPublishedNews(): Promise<NewsSnapshot> {
  const prisma = getPrisma();
  if (!prisma) return emptySnapshot();
  try {
    const rows = await prisma.article.findMany({
      where: { status: "PUBLISHED" },
      orderBy: [{ publishedAt: "desc" }, { createdAt: "desc" }],
      take: PUBLIC_LIMIT,
    });
    const items = rows.flatMap((row) => {
      const item = articleToItem(row);
      return item ? [item] : [];
    });
    const sources = [...new Set(items.map((item) => item.source).filter(Boolean))];
    return {
      items,
      fetchedAt: items[0]?.publishedAt ?? new Date().toISOString(),
      failures: [],
      sources,
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "невідома помилка";
    console.warn(`[varta] опублікована стрічка недоступна: ${reason.slice(0, 180)}`);
    return emptySnapshot();
  }
}
