import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArticleTools } from "@/components/ArticleTools";
import { BookmarkPanel } from "@/components/BookmarkPanel";
import { Cover } from "@/components/Cover";
import { RecordRead } from "@/components/RecordRead";
import { Capsule, StoryRow } from "@/components/Stories";
import { auth } from "@/auth";
import { getPublishedNews } from "@/lib/catalog";
import { categoryLabel } from "@/lib/categories";
import { requirePrisma } from "@/lib/db";
import { formatDateTime, formatWhen } from "@/lib/format";
import { relatedStories } from "@/lib/search";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const snapshot = await getPublishedNews();
  const item = snapshot.items.find((entry) => entry.id === id);
  if (!item) return { title: "Матеріал" };
  return {
    title: item.title,
    description: item.summary || `${item.title}. ${item.source}`.trim(),
  };
}

export default async function ItemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = await getPublishedNews();
  const item = snapshot.items.find((entry) => entry.id === id);
  if (!item) notFound();

  const when = formatDateTime(item.publishedAt);
  const now = Date.now();
  const related = relatedStories(item, snapshot.items, 3);
  const session = await auth();
  const signedIn = Boolean(session?.user);
  let folders: { id: string; name: string }[] = [];
  let saved = false;
  let folderId: string | null = null;
  if (session?.user) {
    const prisma = requirePrisma();
    const [readerFolders, bookmark] = await Promise.all([
      prisma.folder.findMany({
        where: { userId: session.user.id },
        orderBy: { name: "asc" },
        select: { id: true, name: true },
      }),
      prisma.bookmark.findFirst({
        where: { userId: session.user.id, article: { slug: item.id } },
        select: { folderId: true },
      }),
    ]);
    folders = readerFolders;
    saved = Boolean(bookmark);
    folderId = bookmark?.folderId ?? null;
  }

  return (
    <>
      {signedIn ? <RecordRead articleId={item.id} /> : null}
      <ArticleTools articleId={item.id} title={item.title} summary={item.summary} />
      <main id="content" className="mx-auto w-full max-w-[760px] px-4 pb-32 pt-12 sm:px-6">
        <article>
          <div className="flex flex-wrap items-center gap-2">
            <Capsule category={item.category} />
            {item.tags.map((tag) => (
              <Link
                key={tag}
                href={`/search?tag=${encodeURIComponent(tag)}`}
                className="inline-flex items-center rounded-full border border-black/10 px-2.5 py-1 text-[11px] font-medium tracking-wide text-zinc-500 transition-colors hover:text-zinc-950 dark:border-white/10 dark:hover:text-white"
              >
                {tag}
              </Link>
            ))}
          </div>
          <h1 className="mt-5 text-balance text-[2.35rem] font-semibold leading-[1.05] tracking-tight sm:text-5xl">
            {item.title}
          </h1>
          <p className="mt-5 text-sm text-zinc-500">
            {item.source ? (
              <span className="font-medium text-zinc-800 dark:text-zinc-200">{item.source}</span>
            ) : null}
            {item.source && when ? <span aria-hidden="true"> · </span> : null}
            {when ? <time dateTime={item.publishedAt}>{when}</time> : null}
          </p>
          {item.image ? (
            <div className="relative mt-8 aspect-[16/9] overflow-hidden rounded-[28px] bg-zinc-200 dark:bg-white/5">
              <Cover src={item.image} className="absolute inset-0 h-full w-full object-cover" />
            </div>
          ) : null}
          {item.summary ? (
            <p className="mt-10 max-w-[66ch] text-[1.35rem] leading-[1.65] tracking-[-0.011em] text-zinc-800 dark:text-zinc-200">
              {item.summary}
            </p>
          ) : (
            <p className="mt-10 text-lg leading-relaxed text-zinc-500">
              Короткий виклад для цього матеріалу недоступний.
            </p>
          )}
          <BookmarkPanel articleId={item.id} signedIn={signedIn} folders={folders} saved={saved} folderId={folderId} />
          <p className="mt-12 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <Link
              href={`/${item.category}`}
              className="underline decoration-black/20 underline-offset-4 dark:decoration-white/20"
            >
              Усі матеріали розділу «{categoryLabel(item.category)}»
            </Link>
            <Link href="/" className="underline decoration-black/20 underline-offset-4 dark:decoration-white/20">
              На головну
            </Link>
          </p>
        </article>
        {related.length > 0 ? (
          <section className="mt-16 border-t border-black/10 pt-10 dark:border-white/10">
            <h2 className="text-2xl font-semibold tracking-tight">Читайте також</h2>
            <ul className="mt-2">
              {related.map((entry) => (
                <StoryRow key={entry.id} item={entry} when={formatWhen(entry.publishedAt, now)} />
              ))}
            </ul>
          </section>
        ) : null}
      </main>
    </>
  );
}
