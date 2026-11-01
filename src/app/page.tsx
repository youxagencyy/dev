import { FeedStatus } from "@/components/FeedStatus";
import { NewsCard } from "@/components/NewsCard";
import { getNews } from "@/lib/aggregate";
import { formatCount } from "@/lib/format";

export const revalidate = 600;

export default async function HomePage() {
  const snapshot = await getNews();
  const items = snapshot.items.slice(0, 48);
  const [lead, ...rest] = items;

  return (
    <main id="content">
      <div className="wrap">
        <header className="section-head">
          <h1>Останні новини</h1>
          <p className="lede">Заголовки та короткі виклади з усіх розділів.</p>
        </header>
        <FeedStatus snapshot={snapshot} />
        {items.length === 0 ? (
          <div className="empty">
            <p>Стрічка зараз порожня. Джерела тимчасово не відповідають — спробуйте оновити сторінку трохи згодом.</p>
          </div>
        ) : (
          <>
            <p className="status">{formatCount(items.length)}</p>
            {lead ? <NewsCard item={lead} variant="feature" /> : null}
            {rest.length > 0 ? (
              <div className="tile-grid">
                {rest.map((item) => (
                  <NewsCard key={item.id} item={item} />
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
