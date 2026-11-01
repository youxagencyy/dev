import { FEEDS } from "@/lib/feeds";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="wrap">
        <p>
          ВАРТА збирає заголовки та короткі виклади з відкритих стрічок. Повні тексти залишаються в
          редакцій, які їх опублікували.
        </p>
        <p>Стрічки: {FEEDS.map((feed) => feed.name).join(", ")}.</p>
      </div>
    </footer>
  );
}
