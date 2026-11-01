"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main id="content" className="center-note">
      <h1>Не вдалося зібрати стрічку</h1>
      <p>Спробуйте ще раз за мить. Якщо частина джерел мовчить, решта все одно з’явиться.</p>
      <button className="retry" type="button" onClick={() => reset()}>
        Спробувати ще раз
      </button>
    </main>
  );
}
