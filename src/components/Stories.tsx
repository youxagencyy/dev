import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { categoryLabel, type CategorySlug } from "@/lib/categories";
import type { NewsItem } from "@/lib/types";
import { Cover } from "./Cover";

export function Capsule({
  category,
  tone = "neutral",
}: {
  category: CategorySlug;
  tone?: "neutral" | "photo";
}) {
  const label = categoryLabel(category);
  if (tone === "photo") {
    return (
      <span className="inline-flex items-center rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-[11px] font-medium tracking-wide text-white backdrop-blur-[20px]">
        {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full border border-black/10 bg-black/[0.03] px-2.5 py-1 text-[11px] font-medium tracking-wide text-zinc-700 dark:border-white/10 dark:bg-white/[0.06] dark:text-zinc-200">
      {label}
    </span>
  );
}

function Byline({
  source,
  when,
  iso,
  light = false,
}: {
  source: string;
  when: string;
  iso: string;
  light?: boolean;
}) {
  if (!source && !when) return null;
  return (
    <p className={light ? "text-xs text-white/70" : "text-xs text-zinc-500"}>
      {source ? (
        <span className={light ? "font-medium text-white" : "font-medium text-zinc-800 dark:text-zinc-200"}>
          {source}
        </span>
      ) : null}
      {source && when ? <span aria-hidden="true"> · </span> : null}
      {when ? <time dateTime={iso}>{when}</time> : null}
    </p>
  );
}

const zoom =
  "h-full w-full object-cover transition duration-700 ease-out group-hover:scale-[1.045]";

export function LeadCard({ item, when }: { item: NewsItem; when: string }) {
  return (
    <article className="h-full">
      <Link
        href={`/n/${item.id}`}
        className="group relative flex h-full min-h-[520px] overflow-hidden rounded-[28px] border border-black/10 bg-zinc-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:border-white/10 dark:focus-visible:outline-white"
      >
        <Cover src={item.image} className={`absolute inset-0 ${zoom}`} />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-black/10" />
        <div className="relative mt-auto flex max-w-[40rem] flex-col gap-4 p-6 sm:p-8">
          <Capsule category={item.category} tone="photo" />
          <h2 className="text-balance text-3xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl">
            {item.title}
          </h2>
          {item.summary ? (
            <p className="line-clamp-3 max-w-[48ch] text-sm leading-relaxed text-white/75 sm:text-[15px]">
              {item.summary}
            </p>
          ) : null}
          <Byline source={item.source} when={when} iso={item.publishedAt} light />
        </div>
      </Link>
    </article>
  );
}

export function SideCard({ item, when }: { item: NewsItem; when: string }) {
  return (
    <article className="h-full">
      <Link
        href={`/n/${item.id}`}
        className="group grid h-full min-h-[240px] overflow-hidden rounded-[28px] border border-black/10 bg-white/70 backdrop-blur-[20px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:border-white/10 dark:bg-white/[0.03] dark:focus-visible:outline-white sm:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]"
      >
        <div className="relative min-h-[180px] overflow-hidden bg-zinc-200 dark:bg-white/5">
          <Cover src={item.image} className={`absolute inset-0 ${zoom}`} />
        </div>
        <div className="flex flex-col justify-end gap-3 p-5">
          <Capsule category={item.category} />
          <h3 className="text-balance text-xl font-semibold leading-[1.15] tracking-tight">{item.title}</h3>
          <Byline source={item.source} when={when} iso={item.publishedAt} />
        </div>
      </Link>
    </article>
  );
}

export function MiniCard({ item, when }: { item: NewsItem; when: string }) {
  return (
    <article className="h-full">
      <Link
        href={`/n/${item.id}`}
        className="group flex h-full flex-col overflow-hidden rounded-[28px] border border-black/10 bg-white/70 backdrop-blur-[20px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:border-white/10 dark:bg-white/[0.03] dark:focus-visible:outline-white"
      >
        <div className="relative aspect-[16/10] overflow-hidden bg-zinc-200 dark:bg-white/5">
          <Cover src={item.image} className={`absolute inset-0 ${zoom}`} />
        </div>
        <div className="flex flex-1 flex-col gap-2 p-4">
          <Capsule category={item.category} />
          <h3 className="text-[15px] font-semibold leading-snug tracking-tight">{item.title}</h3>
          <div className="mt-auto">
            <Byline source={item.source} when={when} iso={item.publishedAt} />
          </div>
        </div>
      </Link>
    </article>
  );
}

export function Lane({
  title,
  href,
  items,
  times,
}: {
  title: string;
  href: string;
  items: NewsItem[];
  times: Record<string, string>;
}) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <Link
          href={href}
          className="inline-flex items-center gap-1 text-sm text-zinc-500 transition-colors hover:text-zinc-900 dark:hover:text-white"
        >
          Усі
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-sm text-zinc-500">У цій добірці ще тихо.</p>
      ) : (
        <ul className="divide-y divide-black/10 dark:divide-white/10">
          {items.map((item) => (
            <li key={item.id}>
              <Link href={`/n/${item.id}`} className="group block py-3.5">
                <span className="mb-1.5 flex items-center gap-2">
                  <Capsule category={item.category} />
                  {times[item.id] ? (
                    <time dateTime={item.publishedAt} className="text-[11px] text-zinc-500">
                      {times[item.id]}
                    </time>
                  ) : null}
                </span>
                <span className="block text-[15px] font-medium leading-snug tracking-tight transition-colors group-hover:text-zinc-600 dark:group-hover:text-zinc-300">
                  {item.title}
                </span>
                {item.source ? <span className="mt-1 block text-xs text-zinc-500">{item.source}</span> : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function Brief({ items, times }: { items: NewsItem[]; times: Record<string, string> }) {
  return (
    <aside className="rounded-[28px] border border-black/10 bg-white/60 p-5 backdrop-blur-[20px] dark:border-white/10 dark:bg-white/[0.04] lg:sticky lg:top-24">
      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-zinc-500">Бриф</p>
      <h2 className="mt-2 text-balance text-2xl font-semibold leading-[1.1] tracking-tight">
        Головне за 5 хвилин
      </h2>
      {items.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-500">Бриф з’явиться, щойно стрічка відповість.</p>
      ) : (
        <ol className="mt-5 space-y-4">
          {items.map((item, index) => (
            <li key={item.id}>
              <Link href={`/n/${item.id}`} className="group grid grid-cols-[auto_1fr] gap-3">
                <span className="pt-0.5 text-xs tabular-nums text-zinc-400">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span>
                  <span className="block text-sm font-medium leading-snug tracking-tight underline-offset-4 group-hover:underline">
                    {item.title}
                  </span>
                  <span className="mt-1 block text-[11px] text-zinc-500">
                    {item.source}
                    {item.source && times[item.id] ? " · " : ""}
                    {times[item.id] ?? ""}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

export function UrgentList({ items, times }: { items: NewsItem[]; times: Record<string, string> }) {
  if (items.length === 0) return null;
  return (
    <ul className="divide-y divide-black/10 dark:divide-white/10">
      {items.map((item) => (
        <li key={item.id}>
          <Link
            href={`/n/${item.id}`}
            className="group grid grid-cols-1 gap-2 py-4 sm:grid-cols-[7.5rem_1fr] sm:items-baseline sm:gap-6"
          >
            <time dateTime={item.publishedAt} className="text-xs tabular-nums text-zinc-500">
              {times[item.id]}
            </time>
            <span className="min-w-0">
              <span className="mb-1.5 flex items-center gap-2">
                <Capsule category={item.category} />
                {item.source ? <span className="truncate text-[11px] text-zinc-500">{item.source}</span> : null}
              </span>
              <span className="block text-[17px] font-medium leading-snug tracking-tight transition-colors group-hover:text-zinc-600 dark:group-hover:text-zinc-300">
                {item.title}
              </span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function StoryRow({ item, when }: { item: NewsItem; when: string }) {
  return (
    <li className="border-b border-black/10 dark:border-white/10">
      <Link
        href={`/n/${item.id}`}
        className="group grid grid-cols-1 gap-4 py-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-zinc-900 sm:grid-cols-[168px_1fr] sm:items-center dark:focus-visible:outline-white"
      >
        <span className="relative block aspect-[16/10] overflow-hidden rounded-2xl bg-zinc-200 dark:bg-white/5">
          <Cover src={item.image} className={`absolute inset-0 ${zoom}`} />
        </span>
        <span className="min-w-0">
          <span className="flex items-center gap-2">
            <Capsule category={item.category} />
            {when ? (
              <time dateTime={item.publishedAt} className="text-[11px] text-zinc-500">
                {when}
              </time>
            ) : null}
          </span>
          <span className="mt-2 block text-lg font-semibold leading-snug tracking-tight">{item.title}</span>
          {item.summary ? (
            <span className="mt-1 line-clamp-2 block text-sm leading-relaxed text-zinc-500">{item.summary}</span>
          ) : null}
          {item.source ? <span className="mt-2 block text-xs font-medium text-zinc-700 dark:text-zinc-300">{item.source}</span> : null}
        </span>
      </Link>
    </li>
  );
}
