import { Brief, Lane, LeadCard, MiniCard, SideCard, UrgentList } from "@/components/Stories";
import { Magnetic, Reveal } from "@/components/Motion";
import { getNews } from "@/lib/aggregate";
import { formatClock, formatCount, formatWhen } from "@/lib/format";
import { laneItems, pickBrief } from "@/lib/home-feed";

export const revalidate = 600;

export default async function HomePage() {
  const snapshot = await getNews();
  const items = snapshot.items.slice(0, 48);
  const [lead, side, ...afterSide] = items;
  const minis = afterSide.slice(0, 2);
  const bentoIds = new Set([lead, side, ...minis].filter(Boolean).map((item) => item.id));
  const ukraine = laneItems(items, "ukraina", bentoIds);
  const world = laneItems(items, "svit", bentoIds);
  const used = new Set([...bentoIds, ...ukraine.map((item) => item.id), ...world.map((item) => item.id)]);
  const urgent = items.filter((item) => !used.has(item.id)).slice(0, 10);
  const brief = pickBrief(items);
  const times = Object.fromEntries(items.map((item) => [item.id, formatWhen(item.publishedAt)]));
  const clock = formatClock(snapshot.fetchedAt);

  return (
    <main id="content" className="mx-auto w-full max-w-[1240px] px-4 pb-20 pt-8 sm:px-6">
      <header className="mb-8 flex items-end justify-between gap-6">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-zinc-500">Сьогодні</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Стрічка дня</h1>
        </div>
        {items.length > 0 && clock ? (
          <p className="hidden text-sm text-zinc-500 sm:block">Оновлено о {clock}</p>
        ) : null}
      </header>

      {snapshot.failures.length > 0 && items.length > 0 ? (
        <p className="mb-6 text-sm text-zinc-500">Деякі стрічки зараз недоступні. Показано те, що відповіло.</p>
      ) : null}

      {items.length === 0 ? (
        <p className="max-w-md py-16 text-lg leading-relaxed text-zinc-500">
          Стрічка зараз порожня. Джерела тимчасово не відповідають — спробуйте оновити сторінку трохи згодом.
        </p>
      ) : (
        <>
          <section className="grid grid-cols-1 gap-3 lg:grid-cols-12 lg:grid-rows-2">
            {lead ? (
              <Magnetic className="h-full lg:col-span-7 lg:row-span-2">
                <LeadCard item={lead} when={times[lead.id] ?? ""} />
              </Magnetic>
            ) : null}
            {side ? (
              <div className="h-full lg:col-span-5">
                <SideCard item={side} when={times[side.id] ?? ""} />
              </div>
            ) : null}
            {minis.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:col-span-5">
                {minis.map((item) => (
                  <MiniCard key={item.id} item={item} when={times[item.id] ?? ""} />
                ))}
              </div>
            ) : null}
          </section>

          <Reveal className="mt-16 grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-8">
            <div className="lg:col-span-4">
              <Lane title="Україна" href="/ukraina" items={ukraine} times={times} />
            </div>
            <div className="lg:col-span-4">
              <Brief items={brief} times={times} />
            </div>
            <div className="lg:col-span-4">
              <Lane title="Світ" href="/svit" items={world} times={times} />
            </div>
          </Reveal>

          {urgent.length > 0 ? (
            <Reveal className="mt-16">
              <div className="mb-2 flex items-baseline justify-between gap-4">
                <h2 className="text-lg font-semibold tracking-tight">Зараз</h2>
                <p className="text-sm text-zinc-500">{formatCount(items.length)}</p>
              </div>
              <UrgentList items={urgent} times={times} />
            </Reveal>
          ) : null}
        </>
      )}
    </main>
  );
}
