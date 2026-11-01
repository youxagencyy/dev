"use server";

import { Prisma } from "@prisma/client";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { ensureArticle, recordRead } from "@/lib/articles";
import { getNews } from "@/lib/aggregate";
import { CATEGORIES, categoryToEnum, type CategorySlug } from "@/lib/categories";
import { requirePrisma } from "@/lib/db";
import { THEME_COOKIE, parseTheme, themeCookie } from "@/lib/theme";

async function readerId(): Promise<string> {
  const session = await auth();
  if (!session?.user?.id) redirect("/uviity");
  return session.user.id;
}

export async function recordReadAction(articleId: string) {
  const session = await auth();
  if (!session?.user?.id) return;
  const snapshot = await getNews();
  const item = snapshot.items.find((entry) => entry.id === articleId);
  if (!item) return;
  await recordRead(session.user.id, item);
}

export async function createFolderAction(formData: FormData) {
  const userId = await readerId();
  const name = String(formData.get("name") ?? "").trim().replace(/\s+/g, " ").slice(0, 40);
  if (name.length < 2) redirect("/kabinet/zakladky?error=name");
  const prisma = requirePrisma();
  try {
    await prisma.folder.create({ data: { userId, name } });
  } catch (error) {
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      redirect("/kabinet/zakladky?error=exists");
    }
    throw error;
  }
  revalidatePath("/kabinet/zakladky");
  redirect("/kabinet/zakladky");
}

export async function deleteFolderAction(formData: FormData) {
  const userId = await readerId();
  const folderId = String(formData.get("folderId") ?? "");
  const prisma = requirePrisma();
  await prisma.folder.deleteMany({ where: { id: folderId, userId } });
  revalidatePath("/kabinet/zakladky");
  redirect("/kabinet/zakladky");
}

export async function saveBookmarkAction(formData: FormData) {
  const userId = await readerId();
  const slug = String(formData.get("articleId") ?? "");
  const folderId = String(formData.get("folderId") ?? "");
  const snapshot = await getNews();
  const item = snapshot.items.find((entry) => entry.id === slug);
  if (!item) redirect("/");
  const prisma = requirePrisma();
  if (folderId) {
    const folder = await prisma.folder.findFirst({ where: { id: folderId, userId } });
    if (!folder) redirect(`/n/${slug}`);
  }
  const article = await ensureArticle(item);
  await prisma.bookmark.upsert({
    where: { userId_articleId: { userId, articleId: article.id } },
    create: { userId, articleId: article.id, folderId: folderId || null },
    update: { folderId: folderId || null },
  });
  revalidatePath(`/n/${slug}`);
  revalidatePath("/kabinet/zakladky");
}

export async function removeBookmarkAction(formData: FormData) {
  const userId = await readerId();
  const slug = String(formData.get("articleId") ?? "");
  const prisma = requirePrisma();
  await prisma.bookmark.deleteMany({ where: { userId, article: { slug } } });
  revalidatePath(`/n/${slug}`);
  revalidatePath("/kabinet/zakladky");
}

function checkedCategories(formData: FormData, prefix: string): CategorySlug[] {
  return CATEGORIES.map((category) => category.slug).filter(
    (slug) => formData.get(`${prefix}-${slug}`) === "on",
  );
}

export async function saveSettingsAction(formData: FormData) {
  const userId = await readerId();
  const theme = parseTheme(String(formData.get("theme") ?? ""));
  const feed = checkedCategories(formData, "feed");
  if (feed.length === 0) redirect("/kabinet/nalashtuvannia?error=feed");
  const notify = checkedCategories(formData, "note");
  const prisma = requirePrisma();
  await prisma.user.update({
    where: { id: userId },
    data: {
      theme,
      feedCategories: feed.map((slug) => categoryToEnum(slug)),
    },
  });
  await prisma.notificationPref.upsert({
    where: { userId },
    create: {
      userId,
      breaking: formData.get("breaking") === "on",
      dailyBrief: formData.get("dailyBrief") === "on",
      emailEnabled: formData.get("emailEnabled") === "on",
      categories: notify.map((slug) => categoryToEnum(slug)),
    },
    update: {
      breaking: formData.get("breaking") === "on",
      dailyBrief: formData.get("dailyBrief") === "on",
      emailEnabled: formData.get("emailEnabled") === "on",
      categories: notify.map((slug) => categoryToEnum(slug)),
    },
  });
  const jar = await cookies();
  jar.set(THEME_COOKIE, theme, themeCookie);
  revalidatePath("/", "layout");
  redirect("/kabinet/nalashtuvannia?saved=1");
}
