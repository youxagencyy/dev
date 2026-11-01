import type { Metadata } from "next";
import { SearchExplorer } from "@/components/SearchExplorer";
import { getNews } from "@/lib/aggregate";
import { formatWhen } from "@/lib/format";
import { parseSearchFilters } from "@/lib/search";

export const metadata: Metadata = {
  title: "Пошук",
  description: "Пошук матеріалів ВАРТИ за заголовком, розділом, тегом і часом.",
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const initial = parseSearchFilters({
    q: first(params.q),
    category: first(params.category),
    tag: first(params.tag),
    time: first(params.time),
  });
  const snapshot = await getNews();
  const now = Date.now();
  const times = Object.fromEntries(
    snapshot.items.map((item) => [item.id, formatWhen(item.publishedAt, now)]),
  );

  return (
    <main id="content" className="mx-auto w-full max-w-[860px] px-4 pb-24 pt-12 sm:px-6">
      <p className="text-[11px] font-medium tracking-[0.18em] text-zinc-400 uppercase">Пошук</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Знайти матеріал</h1>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-zinc-500">
        Шукає серед заголовків і коротких викладів, які вже є на сайті. Збіги підсвічуються одразу.
      </p>
      <div className="mt-8">
        <SearchExplorer items={snapshot.items} initial={initial} times={times} />
      </div>
    </main>
  );
}
