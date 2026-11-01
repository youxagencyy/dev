"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CATEGORIES } from "@/lib/categories";
import { formatToday } from "@/lib/format";

export function SiteHeader() {
  const pathname = usePathname();
  const section = pathname === "/" ? "home" : pathname.split("/").filter(Boolean)[0];
  const today = formatToday();

  return (
    <header className="site-header">
      <a className="skip" href="#content">
        До змісту
      </a>
      <div className="mast">
        <div className="brand">
          <Link href="/" className="logo">
            ВАРТА
          </Link>
          <p className="tagline">Новини України та світу</p>
        </div>
        <p className="today" suppressHydrationWarning>
          {today}
        </p>
      </div>
      <nav className="sections" aria-label="Розділи">
        <ul>
          <li>
            <Link href="/" aria-current={section === "home" ? "page" : undefined}>
              Головна
            </Link>
          </li>
          {CATEGORIES.map((category) => (
            <li key={category.slug}>
              <Link
                href={`/${category.slug}`}
                aria-current={section === category.slug ? "page" : undefined}
              >
                {category.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
