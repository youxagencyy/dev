import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FeedStatus } from "@/components/FeedStatus";
import { NewsCard } from "@/components/NewsCard";
import { getNews } from "@/lib/aggregate";
import { CATEGORIES, getCategory } from "@/lib/categories";
import { formatCount } from "@/lib/format";

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
    <main id="content">
      <div className="wrap">
        <header className="section-head">
          <h1>{section.label}</h1>
          <p className="lede">{section.blurb}</p>
        </header>
        <FeedStatus snapshot={snapshot} />
        {items.length === 0 ? (
          <div className="empty">
            <p>У розділі «{section.label}» поки немає матеріалів.</p>
          </div>
        ) : (
          <>
            <p className="status">{formatCount(items.length)}</p>
            <div className="story-list">
              {items.map((item) => (
                <NewsCard key={item.id} item={item} variant="row" />
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
