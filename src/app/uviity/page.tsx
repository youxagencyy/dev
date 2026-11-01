import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { loginAction } from "@/app/account/actions";
import { safeNext } from "@/lib/paths";

export const metadata: Metadata = { title: "Увійти" };

const field =
  "mt-2 w-full rounded-2xl border border-black/10 bg-white/70 px-4 py-3 outline-none backdrop-blur-[20px] focus:border-zinc-950 dark:border-white/10 dark:bg-white/[0.04] dark:focus:border-white";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const params = await searchParams;
  const session = await auth();
  const next = safeNext(params.next);
  if (session?.user) redirect(next);

  return (
    <main id="content" className="mx-auto w-full max-w-[440px] px-4 pb-24 pt-16">
      <p className="text-[11px] font-medium tracking-[0.18em] text-zinc-400 uppercase">Обліковий запис</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight">Увійти</h1>
      <form action={loginAction} className="mt-8 space-y-4">
        <input type="hidden" name="next" value={next} />
        <label className="block text-sm">
          Ел. пошта
          <input name="email" type="email" autoComplete="email" required className={field} />
        </label>
        <label className="block text-sm">
          Пароль
          <input name="password" type="password" autoComplete="current-password" required className={field} />
        </label>
        {params.error === "credentials" ? (
          <p className="text-sm text-zinc-700 dark:text-zinc-200">Невірна адреса або пароль.</p>
        ) : null}
        <button type="submit" className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm text-white dark:bg-white dark:text-zinc-950">
          Увійти
        </button>
      </form>
      <p className="mt-6 text-sm text-zinc-500">
        Немає облікового запису?{" "}
        <Link href={`/reiestratsiia?next=${encodeURIComponent(next)}`} className="text-zinc-950 underline decoration-black/20 underline-offset-4 dark:text-white dark:decoration-white/20">
          Зареєструватися
        </Link>
      </p>
    </main>
  );
}
