"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutAction } from "@/app/account/actions";

const links = [
  { href: "/redaktsiia", label: "Черга" },
  { href: "/redaktsiia/dzherela", label: "Джерела" },
];

export function DeskNav() {
  const pathname = usePathname();
  return (
    <div className="mt-6 flex flex-wrap items-center gap-2">
      <nav aria-label="Редакція">
        <ul className="flex flex-wrap gap-2">
          {links.map((link) => {
            const current = pathname === link.href;
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={current ? "page" : undefined}
                  className={`block rounded-full px-3 py-1.5 text-[13px] transition-colors ${
                    current
                      ? "bg-zinc-950 text-white dark:bg-white dark:text-zinc-950"
                      : "border border-black/10 text-zinc-600 hover:bg-black/[0.04] dark:border-white/10 dark:text-zinc-300 dark:hover:bg-white/10"
                  }`}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <form action={logoutAction}>
        <button
          type="submit"
          className="rounded-full px-3 py-1.5 text-[13px] text-zinc-500 hover:text-zinc-950 dark:hover:text-white"
        >
          Вийти
        </button>
      </form>
    </div>
  );
}
