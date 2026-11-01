import Link from "next/link";
import { removeBookmarkAction, saveBookmarkAction } from "@/app/kabinet/actions";

const field =
  "rounded-full border border-black/10 bg-white/70 px-3 py-2 text-sm outline-none dark:border-white/10 dark:bg-white/[0.04]";

export function BookmarkPanel({
  articleId,
  signedIn,
  folders,
  saved,
  folderId,
}: {
  articleId: string;
  signedIn: boolean;
  folders: { id: string; name: string }[];
  saved: boolean;
  folderId: string | null;
}) {
  if (!signedIn) {
    return (
      <p className="mt-8 text-sm text-zinc-500">
        <Link href={`/uviity?next=${encodeURIComponent(`/n/${articleId}`)}`} className="font-medium text-zinc-950 underline decoration-black/20 underline-offset-4 dark:text-white dark:decoration-white/20">
          Увійдіть
        </Link>
        , щоб зберегти матеріал у тему кабінету.
      </p>
    );
  }

  return (
    <div className="mt-8 rounded-[28px] border border-black/10 bg-white/50 p-4 backdrop-blur-[20px] dark:border-white/10 dark:bg-white/[0.04]">
      <p className="text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">Закладка</p>
      <form action={saveBookmarkAction} className="mt-3 flex flex-wrap items-center gap-2">
        <input type="hidden" name="articleId" value={articleId} />
        <label className="sr-only" htmlFor="bookmark-folder">
          Тема
        </label>
        <select id="bookmark-folder" name="folderId" defaultValue={folderId ?? ""} className={field}>
          <option value="">Без теми</option>
          {folders.map((folder) => (
            <option key={folder.id} value={folder.id}>
              {folder.name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-full bg-zinc-950 px-4 py-2 text-sm text-white dark:bg-white dark:text-zinc-950"
        >
          {saved ? "Перемістити" : "Зберегти"}
        </button>
      </form>
      {saved ? (
        <form action={removeBookmarkAction} className="mt-3">
          <input type="hidden" name="articleId" value={articleId} />
          <button type="submit" className="text-sm text-zinc-500 underline decoration-black/20 underline-offset-4">
            Прибрати із закладок
          </button>
        </form>
      ) : (
        <p className="mt-3 text-sm text-zinc-500">
          <Link href="/kabinet/zakladky" className="underline decoration-black/20 underline-offset-4">
            Створити тему
          </Link>
        </p>
      )}
    </div>
  );
}
