import type { Metadata } from "next";
import Link from "next/link";
import { auth } from "@/auth";
import { StoryRow } from "@/components/Stories";
import { getPublishedNews } from "@/lib/catalog";
import { selectedSlugs } from "@/lib/categories";
import { requirePrisma } from "@/lib/db";
import { formatCount, formatWhen } from "@/lib/format";

export const metadata: Metadata = { title: "Моя стрічка" };

export default async function CabinetFeedPage() {
  const session = await auth();
  if (!session?.user) return null;
  const prisma = requirePrisma();
  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: { feedCategories: true },
  });
  const allowed = new Set(selectedSlugs(user?.feedCategories ?? []));
  const snapshot = await getPublishedNews();
  const items = snapshot.items.filter((item) => allowed.size === 0 || allowed.has(item.category)).slice(0, 30);
  const now = Date.now();
  const hidden = 4 - allowed.size;

  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Моя стрічка</h2>
      <p className="mt-2 text-sm text-zinc-500">
        {formatCount(items.length)}
        {hidden > 0 ? `. Сховано розділів: ${hidden}.` : "."}{" "}
        <Link href="/kabinet/nalashtuvannia" className="underline decoration-black/20 underline-offset-4">
          Налаштувати розділи
        </Link>
      </p>
      {items.length === 0 ? (
        <p className="mt-8 text-lg text-zinc-600 dark:text-zinc-300">
          У моїй стрічці зараз порожньо. Увімкніть розділи в налаштуваннях або зачекайте на свіжі матеріали.
        </p>
      ) : (
        <ul className="mt-4">
          {items.map((item) => (
            <StoryRow key={item.id} item={item} when={formatWhen(item.publishedAt, now)} />
          ))}
        </ul>
      )}
    </section>
  );
}
