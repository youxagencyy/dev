"use server";

import { Prisma } from "@prisma/client";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { categoryFromEnum } from "@/lib/categories";
import { parseFeedUrl, parseSourceName } from "@/lib/desk";
import { requireAdmin } from "@/lib/gate";
import { ingestEnabledSources, ingestSource } from "@/lib/ingest";
import { requirePrisma } from "@/lib/db";

async function editor() {
  const admin = await requireAdmin();
  if (!admin) redirect("/redaktsiia");
  return admin;
}

function refreshPublic(slug: string, category: string) {
  revalidatePath("/");
  revalidatePath("/search");
  revalidatePath("/kabinet");
  revalidatePath("/redaktsiia");
  revalidatePath(`/${category}`);
  revalidatePath(`/n/${slug}`);
}

export async function publishAction(formData: FormData) {
  await editor();
  const id = String(formData.get("id") ?? "");
  const prisma = requirePrisma();
  const article = await prisma.article.findUnique({ where: { id } });
  if (!article || article.status !== "DRAFT") redirect("/redaktsiia");
  await prisma.article.update({
    where: { id },
    data: { status: "PUBLISHED", publishedAt: article.publishedAt ?? new Date() },
  });
  refreshPublic(article.slug, categoryFromEnum(article.category) ?? "ukraina");
  redirect("/redaktsiia?published=1");
}

export async function deleteAction(formData: FormData) {
  await editor();
  const id = String(formData.get("id") ?? "");
  const prisma = requirePrisma();
  const article = await prisma.article.findUnique({ where: { id } });
  if (!article || article.status !== "DRAFT") redirect("/redaktsiia");
  await prisma.article.update({ where: { id }, data: { status: "DELETED" } });
  refreshPublic(article.slug, categoryFromEnum(article.category) ?? "ukraina");
  redirect("/redaktsiia?deleted=1");
}

export async function ingestAction() {
  await editor();
  try {
    const result = await ingestEnabledSources();
    const failed = result.failures.length;
    redirect(`/redaktsiia?created=${result.created}&failed=${failed}`);
  } catch (error) {
    if (isNextRedirect(error)) throw error;
    redirect("/redaktsiia?error=ingest");
  }
}

export async function addSourceAction(formData: FormData) {
  await editor();
  const name = parseSourceName(String(formData.get("name") ?? ""));
  const feedUrl = parseFeedUrl(String(formData.get("feedUrl") ?? ""));
  if (!name) redirect("/redaktsiia/dzherela?error=name");
  if (!feedUrl) redirect("/redaktsiia/dzherela?error=url");
  const active = formData.get("enabled") === "on";
  const prisma = requirePrisma();
  try {
    const source = await prisma.source.create({
      data: { name, feedUrl, active, fallback: "UKRAINA" },
    });
    if (!active) redirect("/redaktsiia/dzherela?added=1");
    const result = await ingestSource(source.id);
    redirect(`/redaktsiia?created=${result.created}&failed=${result.failures.length}`);
  } catch (error) {
    if (isNextRedirect(error)) throw error;
    if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002") {
      redirect("/redaktsiia/dzherela?error=exists");
    }
    redirect("/redaktsiia/dzherela?error=ingest");
  }
}

export async function toggleSourceAction(formData: FormData) {
  await editor();
  const id = String(formData.get("id") ?? "");
  const prisma = requirePrisma();
  const source = await prisma.source.findUnique({ where: { id } });
  if (!source) redirect("/redaktsiia/dzherela");
  const active = !source.active;
  await prisma.source.update({ where: { id }, data: { active } });
  if (!active) redirect("/redaktsiia/dzherela?toggled=off");
  try {
    const result = await ingestSource(id);
    redirect(`/redaktsiia/dzherela?toggled=on&created=${result.created}&failed=${result.failures.length}`);
  } catch (error) {
    if (isNextRedirect(error)) throw error;
    redirect("/redaktsiia/dzherela?toggled=on&error=ingest");
  }
}

export async function removeSourceAction(formData: FormData) {
  await editor();
  const id = String(formData.get("id") ?? "");
  const prisma = requirePrisma();
  await prisma.source.deleteMany({ where: { id } });
  redirect("/redaktsiia/dzherela?removed=1");
}

function isNextRedirect(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    String((error as { digest: unknown }).digest).startsWith("NEXT_REDIRECT")
  );
}
