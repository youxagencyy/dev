"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { CATEGORIES, categoryLabel, type CategorySlug } from "@/lib/categories";
import { formatCount } from "@/lib/format";
import {
  filterStories,
  highlightParts,
  popularTags,
  searchHref,
  TIME_WINDOWS,
  type SearchFilters,
  type TimeWindow,
} from "@/lib/search";
import type { NewsItem } from "@/lib/types";

function Marked({ text, query }: { text: string; query: string }) {
  const parts = highlightParts(text, query);
  if (parts.length === 0) return null;
  return parts.map((part, index) =>
    part.hit ? (
      <mark
        key={`${index}-${part.text}`}
        className="rounded-sm bg-amber-200/90 px-0.5 text-inherit dark:bg-amber-200/25"
      >
        {part.text}
      </mark>
    ) : (
      <span key={`${index}-${part.text}`}>{part.text}</span>
    ),
  );
}

const chip =
  "rounded-full border px-3 py-1.5 text-[13px] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:focus-visible:outline-white";

function Chip({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`${chip} ${
        pressed
          ? "border-transparent bg-zinc-950 text-white dark:bg-white dark:text-zinc-950"
          : "border-black/10 text-zinc-600 hover:bg-black/[0.04] hover:text-zinc-950 dark:border-white/10 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white"
      }`}
    >
      {children}
    </button>
  );
}

export function SearchExplorer({
  items,
  initial,
  times,
}: {
  items: NewsItem[];
  initial: SearchFilters;
  times: Record<string, string>;
}) {
  const [query, setQuery] = useState(initial.query);
  const [category, setCategory] = useState<CategorySlug | "all">(initial.category);
  const [tag, setTag] = useState(initial.tag);
  const [time, setTime] = useState<TimeWindow>(initial.time);

  const filters = useMemo<SearchFilters>(
    () => ({ query, category, tag, time }),
    [query, category, tag, time],
  );

  useEffect(() => {
    const href = searchHref(filters);
    if (`${window.location.pathname}${window.location.search}` !== href) {
      window.history.replaceState(null, "", href);
    }
  }, [filters]);

  const results = useMemo(() => filterStories(items, filters), [items, filters]);
  const tags = useMemo(() => {
    const popular = popularTags(items);
    if (tag && !popular.includes(tag)) return [tag, ...popular];
    return popular;
  }, [items, tag]);

  return (
    <div>
      <label className="relative block">
        <span className="sr-only">Пошук матеріалів</span>
        <Search
          size={18}
          strokeWidth={1.75}
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400"
        />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Заголовок, виклад, редакція або тег"
          autoComplete="off"
          autoFocus
          className="w-full rounded-full border border-black/10 bg-white/70 py-4 pl-12 pr-5 text-lg tracking-tight outline-none backdrop-blur-[20px] placeholder:text-zinc-400 focus:border-zinc-950 dark:border-white/10 dark:bg-white/[0.04] dark:focus:border-white"
        />
      </label>

      <div className="mt-6 space-y-4">
        <FilterRow label="Розділ">
          <Chip pressed={category === "all"} onClick={() => setCategory("all")}>
            Усі
          </Chip>
          {CATEGORIES.map((entry) => (
            <Chip
              key={entry.slug}
              pressed={category === entry.slug}
              onClick={() => setCategory(entry.slug)}
            >
              {entry.label}
            </Chip>
          ))}
        </FilterRow>
        {tags.length > 0 ? (
          <FilterRow label="Теги">
            <Chip pressed={tag === ""} onClick={() => setTag("")}>
              Усі
            </Chip>
            {tags.map((entry) => (
              <Chip key={entry} pressed={tag === entry} onClick={() => setTag(tag === entry ? "" : entry)}>
                {entry}
              </Chip>
            ))}
          </FilterRow>
        ) : null}
        <FilterRow label="Час">
          {TIME_WINDOWS.map((window) => (
            <Chip key={window.id} pressed={time === window.id} onClick={() => setTime(window.id)}>
              {window.label}
            </Chip>
          ))}
        </FilterRow>
      </div>

      <p className="mt-8 text-sm text-zinc-500">{formatCount(results.length)}</p>

      {results.length === 0 ? (
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-zinc-600 dark:text-zinc-300">
          За цим запитом матеріалів немає. Спробуйте інший розділ, тег або коротший запит.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-black/10 dark:divide-white/10">
          {results.map((item) => (
            <li key={item.id}>
              <Link
                href={`/n/${item.id}`}
                className="group block py-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-zinc-900 dark:focus-visible:outline-white"
              >
                <span className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
                  <span className="rounded-full border border-black/10 px-2 py-0.5 text-zinc-700 dark:border-white/10 dark:text-zinc-200">
                    {categoryLabel(item.category)}
                  </span>
                  {item.source ? <span>{item.source}</span> : null}
                  {times[item.id] ? <time dateTime={item.publishedAt}>{times[item.id]}</time> : null}
                </span>
                <span className="mt-2 block text-xl font-semibold leading-snug tracking-tight">
                  <Marked text={item.title} query={query} />
                </span>
                {item.summary ? (
                  <span className="mt-1 block text-sm leading-relaxed text-zinc-500">
                    <Marked text={item.summary} query={query} />
                  </span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">{label}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}
