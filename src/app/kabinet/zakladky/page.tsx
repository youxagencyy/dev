import type { Metadata } from "next";
import { auth } from "@/auth";
import { StoryRow } from "@/components/Stories";
import { createFolderAction, deleteFolderAction } from "@/app/kabinet/actions";
import { articleToItem } from "@/lib/articles";
import { requirePrisma } from "@/lib/db";
import { formatWhen } from "@/lib/format";

export const metadata: Metadata = { title: "Закладки" };

const field =
  "rounded-full border border-black/10 bg-white/70 px-4 py-2 text-sm outline-none dark:border-white/10 dark:bg-white/[0.04]";

const errors: Record<string, string> = {
  name: "Назва теми має містити щонайменше два символи.",
  exists: "Така тема вже є.",
};

export default async function BookmarksPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const params = await searchParams;
  const session = await auth();
  if (!session?.user) return null;
  const prisma = requirePrisma();
  const [folders, loose] = await Promise.all([
    prisma.folder.findMany({
      where: { userId: session.user.id },
      orderBy: { name: "asc" },
      include: {
        bookmarks: { orderBy: { createdAt: "desc" }, include: { article: true } },
      },
    }),
    prisma.bookmark.findMany({
      where: { userId: session.user.id, folderId: null },
      orderBy: { createdAt: "desc" },
      include: { article: true },
    }),
  ]);
  const now = Date.now();

  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Закладки</h2>
      <p className="mt-2 text-sm text-zinc-500">Теми зберігаються в базі. Матеріал можна покласти в тему зі сторінки читання.</p>
      <form action={createFolderAction} className="mt-6 flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="folder-name">
          Назва теми
        </label>
        <input id="folder-name" name="name" placeholder="Назва теми" maxLength={40} className={field} />
        <button type="submit" className="rounded-full bg-zinc-950 px-4 py-2 text-sm text-white dark:bg-white dark:text-zinc-950">
          Створити тему
        </button>
      </form>
      {params.error && errors[params.error] ? (
        <p className="mt-3 text-sm text-zinc-700 dark:text-zinc-200">{errors[params.error]}</p>
      ) : null}

      {folders.length === 0 && loose.length === 0 ? (
        <p className="mt-8 text-lg text-zinc-600 dark:text-zinc-300">Ще немає тем і закладок.</p>
      ) : null}

      <div className="mt-8 space-y-10">
        {folders.map((folder) => (
          <section key={folder.id}>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold tracking-tight">{folder.name}</h3>
              <form action={deleteFolderAction}>
                <input type="hidden" name="folderId" value={folder.id} />
                <button type="submit" className="text-sm text-zinc-500 underline decoration-black/20 underline-offset-4">
                  Видалити тему
                </button>
              </form>
            </div>
            {folder.bookmarks.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-500">У цій темі ще немає матеріалів.</p>
            ) : (
              <ul>
                {folder.bookmarks.map((bookmark) => {
                  const item = articleToItem(bookmark.article);
                  if (!item) return null;
                  return <StoryRow key={bookmark.id} item={item} when={formatWhen(bookmark.createdAt.toISOString(), now)} />;
                })}
              </ul>
            )}
          </section>
        ))}
        {loose.length > 0 ? (
          <section>
            <h3 className="text-lg font-semibold tracking-tight">Без теми</h3>
            <ul>
              {loose.map((bookmark) => {
                const item = articleToItem(bookmark.article);
                if (!item) return null;
                return <StoryRow key={bookmark.id} item={item} when={formatWhen(bookmark.createdAt.toISOString(), now)} />;
              })}
            </ul>
          </section>
        ) : null}
      </div>
    </section>
  );
}
