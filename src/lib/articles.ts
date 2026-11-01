import type { ArticleCategory } from "@prisma/client";
import { categoryFromEnum } from "./categories";
import { requirePrisma } from "./db";
import type { NewsItem } from "./types";

export async function recordRead(userId: string, slug: string) {
  const prisma = requirePrisma();
  const article = await prisma.article.findFirst({
    where: { slug, status: "PUBLISHED" },
    select: { id: true },
  });
  if (!article) return;
  const existing = await prisma.readEvent.findFirst({
    where: { userId, articleId: article.id },
    orderBy: { readAt: "desc" },
  });
  if (existing) {
    await prisma.readEvent.update({
      where: { id: existing.id },
      data: { readAt: new Date() },
    });
    return;
  }
  await prisma.readEvent.create({
    data: { userId, articleId: article.id },
  });
}

export function articleToItem(article: {
  slug: string;
  title: string;
  summaryBullets: string[];
  outletName: string;
  publishedAt: Date | null;
  createdAt: Date;
  category: ArticleCategory;
  tags: string[];
  coverUrl: string | null;
}): NewsItem | null {
  const category = categoryFromEnum(article.category);
  if (!category) return null;
  return {
    id: article.slug,
    title: article.title,
    summary: article.summaryBullets[0] ?? "",
    source: article.outletName,
    publishedAt: (article.publishedAt ?? article.createdAt).toISOString(),
    category,
    tags: article.tags,
    ...(article.coverUrl ? { image: article.coverUrl } : {}),
  };
}
