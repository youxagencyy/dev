import { FEEDS } from "@/lib/feeds";

export function SiteFooter() {
  return (
    <footer className="mt-8 border-t border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-[1240px] flex-col gap-2 px-4 py-8 text-xs leading-relaxed text-zinc-500 sm:px-6">
        <p>ВАРТА збирає заголовки та короткі виклади. Повні тексти залишаються в редакцій, які їх опублікували.</p>
        <p>Стрічки: {FEEDS.map((feed) => feed.name).join(", ")}.</p>
      </div>
    </footer>
  );
}
