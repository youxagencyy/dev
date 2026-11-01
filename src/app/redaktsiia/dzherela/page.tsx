import type { Metadata } from "next";
import { addSourceAction, removeSourceAction, toggleSourceAction } from "@/app/redaktsiia/actions";
import { requirePrisma } from "@/lib/db";
import { requireAdmin } from "@/lib/gate";

export const metadata: Metadata = { title: "Джерела" };

const field =
  "mt-2 w-full rounded-2xl border border-black/10 bg-white/70 px-4 py-3 outline-none backdrop-blur-[20px] focus:border-zinc-950 dark:border-white/10 dark:bg-white/[0.04] dark:focus:border-white";

export default async function SourcesPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; added?: string; removed?: string; toggled?: string; created?: string; failed?: string }>;
}) {
  const admin = await requireAdmin();
  if (!admin) return null;
  const params = await searchParams;
  const prisma = requirePrisma();
  const sources = await prisma.source.findMany({ orderBy: { name: "asc" } });
  const created = Number(params.created ?? "");
  const failed = Number(params.failed ?? "");

  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Джерела</h2>
      <p className="mt-2 max-w-xl text-sm text-zinc-500">
        Увімкнене джерело можна зібрати в чергу. Вимкнене лишається в списку і не опитується. Збій збору не знімає вже опубліковані матеріали.
      </p>

      <SourceNotice
        error={params.error ?? null}
        added={params.added === "1"}
        removed={params.removed === "1"}
        toggled={params.toggled ?? null}
        created={created}
        failed={failed}
      />

      <form action={addSourceAction} className="mt-8 space-y-4 rounded-[28px] border border-black/10 p-5 dark:border-white/10">
        <p className="text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">Нове джерело</p>
        <label className="block text-sm">
          Назва
          <input name="name" required minLength={2} maxLength={80} className={field} />
        </label>
        <label className="block text-sm">
          Адреса стрічки
          <input name="feedUrl" type="url" required inputMode="url" placeholder="https://" className={field} />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="enabled" defaultChecked className="size-4 accent-zinc-950 dark:accent-white" />
          Увімкнене
        </label>
        <button type="submit" className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm text-white dark:bg-white dark:text-zinc-950">
          Додати джерело
        </button>
      </form>

      {sources.length === 0 ? (
        <p className="mt-8 text-lg text-zinc-600 dark:text-zinc-300">Джерел поки немає.</p>
      ) : (
        <ul className="mt-8 divide-y divide-black/10 dark:divide-white/10">
          {sources.map((source) => (
            <li key={source.id} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-medium tracking-tight">{source.name}</p>
                <p className="mt-1 break-all text-sm text-zinc-500">{source.feedUrl}</p>
                <p className="mt-1 text-[11px] tracking-wide text-zinc-400 uppercase">
                  {source.active ? "Увімкнено" : "Вимкнено"}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <form action={toggleSourceAction}>
                  <input type="hidden" name="id" value={source.id} />
                  <button
                    type="submit"
                    className="rounded-full border border-black/10 px-4 py-2 text-sm text-zinc-800 dark:border-white/10 dark:text-zinc-100"
                  >
                    {source.active ? "Вимкнути" : "Увімкнути"}
                  </button>
                </form>
                <form action={removeSourceAction}>
                  <input type="hidden" name="id" value={source.id} />
                  <button
                    type="submit"
                    className="rounded-full px-4 py-2 text-sm text-zinc-500 hover:text-zinc-950 dark:hover:text-white"
                  >
                    Прибрати
                  </button>
                </form>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SourceNotice({
  error,
  added,
  removed,
  toggled,
  created,
  failed,
}: {
  error: string | null;
  added: boolean;
  removed: boolean;
  toggled: string | null;
  created: number;
  failed: number;
}) {
  const lines: string[] = [];
  if (error === "name") lines.push("Назва має містити хоча б два символи.");
  if (error === "url") lines.push("Потрібна адреса стрічки, що починається з http або https.");
  if (error === "exists") lines.push("Джерело з такою адресою вже є.");
  if (error === "ingest") lines.push("Джерело збережено, але збір не вдався. Сайт лишився з опублікованими матеріалами.");
  if (added) lines.push("Джерело додано й вимкнене, тож у чергу воно ще не пише.");
  if (removed) lines.push("Джерело прибрано.");
  if (toggled === "off") lines.push("Джерело вимкнено. Наступний збір його пропустить.");
  if (toggled === "on") {
    lines.push("Джерело увімкнено.");
    if (Number.isFinite(created) && created > 0) lines.push(`Нових чернеток: ${created}.`);
    if (Number.isFinite(failed) && failed > 0) lines.push("Стрічка не відповіла. Опубліковані матеріали на місці.");
  }
  if (lines.length === 0) return null;
  return (
    <p className="mt-4 text-sm text-zinc-700 dark:text-zinc-200" role="status">
      {lines.join(" ")}
    </p>
  );
}
