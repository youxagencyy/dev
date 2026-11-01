import type { ArticleCategory } from "@prisma/client";
import { categoryFromEnum, categoryToEnum } from "./categories";
import { requirePrisma } from "./db";
import type { NewsItem } from "./types";

export async function ensureArticle(item: NewsItem) {
  const prisma = requirePrisma();
  const category = categoryToEnum(item.category) as ArticleCategory;
  const publishedAt = Number.isNaN(Date.parse(item.publishedAt)) ? null : new Date(item.publishedAt);
  const summaryBullets = item.summary ? [item.summary] : [];

  return prisma.article.upsert({
    where: { slug: item.id },
    create: {
      slug: item.id,
      title: item.title,
      rewrittenBody: "",
      summaryBullets,
      tags: item.tags,
      coverUrl: item.image ?? null,
      category,
      status: "PUBLISHED",
      outletName: item.source || "ВАРТА",
      publishedAt,
    },
    update: {
      title: item.title,
      summaryBullets,
      tags: item.tags,
      coverUrl: item.image ?? null,
      category,
      outletName: item.source || "ВАРТА",
      publishedAt,
      status: "PUBLISHED",
    },
  });
}

export async function recordRead(userId: string, item: NewsItem) {
  const prisma = requirePrisma();
  const article = await ensureArticle(item);
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
