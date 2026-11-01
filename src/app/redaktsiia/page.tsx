import type { Metadata } from "next";
import Link from "next/link";
import { deleteAction, ingestAction, publishAction } from "@/app/redaktsiia/actions";
import { Capsule } from "@/components/Stories";
import { categoryFromEnum } from "@/lib/categories";
import { requirePrisma } from "@/lib/db";
import { formatCount, formatWhen } from "@/lib/format";
import { requireAdmin } from "@/lib/gate";

export const metadata: Metadata = { title: "Черга" };

const QUEUE_LIMIT = 40;

export default async function QueuePage({
  searchParams,
}: {
  searchParams: Promise<{ published?: string; deleted?: string; created?: string; failed?: string; error?: string }>;
}) {
  const admin = await requireAdmin();
  if (!admin) return null;
  const params = await searchParams;
  const prisma = requirePrisma();
  const [drafts, total] = await Promise.all([
    prisma.article.findMany({
      where: { status: "DRAFT" },
      orderBy: [{ publishedAt: "desc" }, { createdAt: "desc" }],
      take: QUEUE_LIMIT,
      include: { source: { select: { name: true } } },
    }),
    prisma.article.count({ where: { status: "DRAFT" } }),
  ]);
  const now = Date.now();
  const created = Number(params.created ?? "");
  const failed = Number(params.failed ?? "");

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Черга</h2>
          <p className="mt-2 max-w-xl text-sm text-zinc-500">
            Нові матеріали з увімкнених джерел чекають тут. На сайт потрапляє лише те, що опубліковано.
          </p>
        </div>
        <form action={ingestAction}>
          <button
            type="submit"
            className="rounded-full border border-black/10 px-4 py-2 text-sm text-zinc-800 dark:border-white/10 dark:text-zinc-100"
          >
            Зібрати зараз
          </button>
        </form>
      </div>

      <DeskNotice
        published={params.published === "1"}
        deleted={params.deleted === "1"}
        gathered={params.created !== undefined}
        created={created}
        failed={failed}
        error={params.error === "ingest"}
      />

      <p className="mt-6 text-sm text-zinc-500">
        {formatCount(total)} у черзі.
        {total > drafts.length ? ` Показано перші ${drafts.length}.` : ""}
      </p>

      {drafts.length === 0 ? (
        <p className="mt-8 text-lg text-zinc-600 dark:text-zinc-300">
          Черга порожня.{" "}
          <Link href="/redaktsiia/dzherela" className="underline decoration-black/20 underline-offset-4">
            Зберіть джерела
          </Link>
          , щоб з’явилися чернетки.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-black/10 dark:divide-white/10">
          {drafts.map((article) => {
            const category = categoryFromEnum(article.category);
            const when = formatWhen((article.publishedAt ?? article.createdAt).toISOString(), now);
            const summary = article.summaryBullets[0] ?? "";
            return (
              <li key={article.id} className="py-5">
                <div className="flex flex-wrap items-center gap-2">
                  {category ? <Capsule category={category} /> : null}
                  <span className="text-[11px] text-zinc-500">{article.source?.name || article.outletName}</span>
                  {when ? <time className="text-[11px] text-zinc-500">{when}</time> : null}
                </div>
                <h3 className="mt-2 text-lg font-semibold leading-snug tracking-tight">{article.title}</h3>
                {summary ? <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-zinc-500">{summary}</p> : null}
                <div className="mt-4 flex flex-wrap gap-2">
                  <form action={publishAction}>
                    <input type="hidden" name="id" value={article.id} />
                    <button
                      type="submit"
                      className="rounded-full bg-zinc-950 px-4 py-2 text-sm text-white dark:bg-white dark:text-zinc-950"
                    >
                      Опублікувати
                    </button>
                  </form>
                  <form action={deleteAction}>
                    <input type="hidden" name="id" value={article.id} />
                    <button
                      type="submit"
                      className="rounded-full border border-black/10 px-4 py-2 text-sm text-zinc-600 dark:border-white/10 dark:text-zinc-300"
                    >
                      Видалити
                    </button>
                  </form>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function DeskNotice({
  published,
  deleted,
  gathered,
  created,
  failed,
  error,
}: {
  published: boolean;
  deleted: boolean;
  gathered: boolean;
  created: number;
  failed: number;
  error: boolean;
}) {
  const lines: string[] = [];
  if (published) lines.push("Матеріал опубліковано і вже на сайті.");
  if (deleted) lines.push("Матеріал прибрано. На сайті його немає.");
  if (gathered && Number.isFinite(created) && created > 0) lines.push(`Нових чернеток: ${created}.`);
  if (gathered && created === 0 && failed === 0) {
    lines.push("Нових чернеток немає. Опублікована стрічка без змін.");
  }
  if (Number.isFinite(failed) && failed > 0) {
    lines.push(
      created > 0
        ? `Не відповіли джерел: ${failed}. Опублікована стрічка лишилася на місці.`
        : "Увімкнені джерела не відповіли. Опублікована стрічка лишилася на місці.",
    );
  }
  if (error) lines.push("Збір не вдався. Опублікована стрічка лишилася на місці.");
  if (lines.length === 0) return null;
  return (
    <p className="mt-4 text-sm text-zinc-700 dark:text-zinc-200" role="status">
      {lines.join(" ")}
    </p>
  );
}
