import Link from "next/link";

export function DeskRefusal() {
  return (
    <main id="content" className="mx-auto w-full max-w-[720px] px-4 pb-24 pt-16 sm:px-6">
      <p className="text-[11px] font-medium tracking-[0.18em] text-zinc-400 uppercase">Редакція</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Доступ заборонено</h1>
      <p className="mt-4 max-w-md text-lg leading-relaxed text-zinc-600 dark:text-zinc-300">
        Цей розділ відкритий лише для редакторів. Обліковий запис читача сюди не проходить.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex rounded-full bg-zinc-950 px-5 py-2.5 text-sm text-white dark:bg-white dark:text-zinc-950"
      >
        На головну
      </Link>
    </main>
  );
}
