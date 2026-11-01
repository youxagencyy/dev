import type { Metadata } from "next";
import { auth } from "@/auth";
import { SettingsForm } from "@/components/SettingsForm";
import { CATEGORIES, selectedSlugs } from "@/lib/categories";
import { requirePrisma } from "@/lib/db";
import { parseTheme } from "@/lib/theme";

export const metadata: Metadata = { title: "Налаштування" };

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ saved?: string; error?: string }>;
}) {
  const params = await searchParams;
  const session = await auth();
  if (!session?.user) return null;
  const prisma = requirePrisma();
  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    include: { notificationPref: true },
  });
  if (!user) return null;
  const all = CATEGORIES.map((category) => category.slug);

  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Налаштування</h2>
      <div className="mt-8">
        <SettingsForm
          theme={parseTheme(user.theme)}
          feed={selectedSlugs(user.feedCategories)}
          notify={selectedSlugs(user.notificationPref?.categories ?? all)}
          breaking={user.notificationPref?.breaking ?? true}
          dailyBrief={user.notificationPref?.dailyBrief ?? true}
          emailEnabled={user.notificationPref?.emailEnabled ?? false}
          saved={params.saved === "1"}
          error={params.error ?? null}
        />
      </div>
    </section>
  );
}
