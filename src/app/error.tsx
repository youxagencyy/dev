"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main id="content" className="mx-auto max-w-[1240px] px-4 py-24 sm:px-6">
      <h1 className="text-4xl font-semibold tracking-tight">Не вдалося зібрати стрічку</h1>
      <p className="mt-3 max-w-md text-zinc-500">
        Спробуйте ще раз за мить. Якщо частина джерел мовчить, решта все одно з’явиться.
      </p>
      <button
        className="mt-8 rounded-full bg-zinc-950 px-4 py-2 text-sm text-white dark:bg-white dark:text-zinc-950"
        type="button"
        onClick={() => reset()}
      >
        Спробувати ще раз
      </button>
    </main>
  );
}
