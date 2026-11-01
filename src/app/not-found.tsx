import Link from "next/link";

export default function NotFound() {
  return (
    <main id="content" className="mx-auto max-w-[1240px] px-4 py-24 sm:px-6">
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-zinc-500">404</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight">Матеріал не знайдено</h1>
      <p className="mt-3 max-w-md text-zinc-500">Можливо, він уже зник зі свіжої стрічки.</p>
      <Link
        href="/"
        className="mt-8 inline-flex rounded-full bg-zinc-950 px-4 py-2 text-sm text-white dark:bg-white dark:text-zinc-950"
      >
        На головну
      </Link>
    </main>
  );
}
