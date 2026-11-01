"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CATEGORIES } from "@/lib/categories";
import { formatToday } from "@/lib/format";

const links = [{ href: "/", label: "Головна", id: "home" }, ...CATEGORIES.map((category) => ({
  href: `/${category.slug}`,
  label: category.label,
  id: category.slug,
}))];

export function SiteHeader() {
  const pathname = usePathname();
  const section = pathname === "/" ? "home" : pathname.split("/").filter(Boolean)[0];
  const today = formatToday();

  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-[#f6f6f7]/70 backdrop-blur-[20px] dark:border-white/10 dark:bg-[#0A0A0C]/70">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-full focus:bg-zinc-950 focus:px-3 focus:py-1 focus:text-sm focus:text-white"
      >
        До змісту
      </a>
      <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="shrink-0 text-[13px] font-semibold tracking-[0.22em]">
          ВАРТА
        </Link>
        <nav aria-label="Розділи" className="min-w-0 flex-1">
          <ul className="flex items-center gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {links.map((link) => {
              const current = section === link.id;
              return (
                <li key={link.id}>
                  <Link
                    href={link.href}
                    aria-current={current ? "page" : undefined}
                    className={`block whitespace-nowrap rounded-full px-3 py-1.5 text-[13px] transition-colors ${
                      current
                        ? "bg-zinc-950 text-white dark:bg-white dark:text-zinc-950"
                        : "text-zinc-600 hover:bg-black/5 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <p className="hidden shrink-0 text-xs text-zinc-500 lg:block" suppressHydrationWarning>
          {today}
        </p>
      </div>
    </header>
  );
}
