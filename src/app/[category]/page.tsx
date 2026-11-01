import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { StoryRow } from "@/components/Stories";
import { getNews } from "@/lib/aggregate";
import { CATEGORIES, getCategory } from "@/lib/categories";
import { formatCount, formatWhen } from "@/lib/format";

export const revalidate = 600;
export const dynamicParams = false;

export function generateStaticParams() {
  return CATEGORIES.map((category) => ({ category: category.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>;
}): Promise<Metadata> {
  const { category } = await params;
  const section = getCategory(category);
  if (!section) return { title: "Розділ" };
  return { title: section.label, description: section.blurb };
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;
  const section = getCategory(category);
  if (!section) notFound();

  const snapshot = await getNews();
  const items = snapshot.items.filter((item) => item.category === section.slug).slice(0, 40);

  return (
    <main id="content" className="mx-auto w-full max-w-[1240px] px-4 pb-20 pt-10 sm:px-6">
      <header className="mb-8 max-w-2xl">
        <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-zinc-500">Розділ</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">{section.label}</h1>
        <p className="mt-3 text-zinc-500">{section.blurb}</p>
        {items.length > 0 ? <p className="mt-4 text-sm text-zinc-500">{formatCount(items.length)}</p> : null}
      </header>
      {items.length === 0 ? (
        <p className="text-zinc-500">У розділі «{section.label}» поки немає матеріалів.</p>
      ) : (
        <ul>
          {items.map((item) => (
            <StoryRow key={item.id} item={item} when={formatWhen(item.publishedAt)} />
          ))}
        </ul>
      )}
    </main>
  );
}
