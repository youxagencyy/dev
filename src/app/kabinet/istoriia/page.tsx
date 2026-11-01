import type { Metadata } from "next";
import { auth } from "@/auth";
import { StoryRow } from "@/components/Stories";
import { articleToItem } from "@/lib/articles";
import { requirePrisma } from "@/lib/db";
import { formatWhen } from "@/lib/format";

export const metadata: Metadata = { title: "Історія" };

export default async function HistoryPage() {
  const session = await auth();
  if (!session?.user) return null;
  const prisma = requirePrisma();
  const reads = await prisma.readEvent.findMany({
    where: { userId: session.user.id },
    orderBy: { readAt: "desc" },
    include: { article: true },
    take: 40,
  });
  const now = Date.now();

  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Історія</h2>
      <p className="mt-2 text-sm text-zinc-500">Матеріали, які ви відкривали, поки були в обліковому записі.</p>
      {reads.length === 0 ? (
        <p className="mt-8 text-lg text-zinc-600 dark:text-zinc-300">Відкрийте будь-який матеріал, і він з’явиться тут.</p>
      ) : (
        <ul className="mt-4">
          {reads.map((read) => {
            const item = articleToItem(read.article);
            if (!item) return null;
            return <StoryRow key={read.id} item={item} when={formatWhen(read.readAt.toISOString(), now)} />;
          })}
        </ul>
      )}
    </section>
  );
}
