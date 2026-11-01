import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Cover } from "@/components/Cover";
import { Capsule } from "@/components/Stories";
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
    <main id="content" className="mx-auto w-full max-w-[760px] px-4 pb-24 pt-10 sm:px-6">
      <article>
        <Capsule category={item.category} />
        <h1 className="mt-4 text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">
          {item.title}
        </h1>
        <p className="mt-4 text-sm text-zinc-500">
          {item.source ? <span className="font-medium text-zinc-800 dark:text-zinc-200">{item.source}</span> : null}
          {item.source && when ? <span aria-hidden="true"> · </span> : null}
          {when ? <time dateTime={item.publishedAt}>{when}</time> : null}
        </p>
        {item.image ? (
          <div className="relative mt-8 aspect-[16/9] overflow-hidden rounded-[28px] bg-zinc-200 dark:bg-white/5">
            <Cover src={item.image} className="absolute inset-0 h-full w-full object-cover" />
          </div>
        ) : null}
        {item.summary ? (
          <p className="mt-8 max-w-[68ch] text-xl leading-relaxed text-zinc-700 dark:text-zinc-300">{item.summary}</p>
        ) : (
          <p className="mt-8 text-lg text-zinc-500">Короткий виклад для цього матеріалу недоступний.</p>
        )}
        <p className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Link href={`/${item.category}`} className="underline decoration-black/20 underline-offset-4 dark:decoration-white/20">
            Усі матеріали розділу «{categoryLabel(item.category)}»
          </Link>
          <Link href="/" className="underline decoration-black/20 underline-offset-4 dark:decoration-white/20">
            На головну
          </Link>
        </p>
      </article>
    </main>
  );
}
