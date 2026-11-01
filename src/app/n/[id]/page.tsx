import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CoverImage } from "@/components/CoverImage";
import { getNews } from "@/lib/aggregate";
import { categoryLabel } from "@/lib/categories";
import { formatDateTime } from "@/lib/format";

export const revalidate = 600;

export async function generateStaticParams() {
  const snapshot = await getNews();
  return snapshot.items.slice(0, 40).map((item) => ({ id: item.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const snapshot = await getNews();
  const item = snapshot.items.find((entry) => entry.id === id);
  if (!item) return { title: "Матеріал" };
  return {
    title: item.title,
    description: item.summary || `${item.title}. ${item.source}`.trim(),
  };
}

export default async function ItemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = await getNews();
  const item = snapshot.items.find((entry) => entry.id === id);
  if (!item) notFound();

  const when = formatDateTime(item.publishedAt);

  return (
    <main id="content">
      <div className="wrap">
        <article className="detail" data-cat={item.category}>
          <p className="kicker">{categoryLabel(item.category)}</p>
          <h1>{item.title}</h1>
          <p className="meta">
            {item.source ? <span className="source">{item.source}</span> : null}
            {item.source && when ? <span aria-hidden="true"> · </span> : null}
            {when ? <time dateTime={item.publishedAt}>{when}</time> : null}
          </p>
          {item.image ? <CoverImage src={item.image} /> : null}
          {item.summary ? (
            <p className="summary">{item.summary}</p>
          ) : (
            <p className="summary">Короткий виклад для цього матеріалу недоступний.</p>
          )}
          <p className="back">
            <Link className="text-link" href={`/${item.category}`}>
              Усі матеріали розділу «{categoryLabel(item.category)}»
            </Link>
            <Link className="text-link" href="/">
              На головну
            </Link>
          </p>
        </article>
      </div>
    </main>
  );
}
