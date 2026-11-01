import Link from "next/link";

export default function NotFound() {
  return (
    <main id="content" className="center-note">
      <h1>Матеріал не знайдено</h1>
      <p>Можливо, він уже зник зі свіжої стрічки.</p>
      <p>
        <Link className="text-link" href="/">
          На головну
        </Link>
      </p>
    </main>
  );
}
