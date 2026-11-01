"use client";

import { useEffect, useState } from "react";
import { Heart, Share2, Volume2 } from "lucide-react";

const control =
  "inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-[13px] text-zinc-800 transition-colors hover:bg-black/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:text-zinc-100 dark:hover:bg-white/10 dark:focus-visible:outline-white";

export function ArticleTools({
  articleId,
  title,
  summary,
}: {
  articleId: string;
  title: string;
  summary: string;
}) {
  const [progress, setProgress] = useState(0);
  const [liked, setLiked] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [note, setNote] = useState("");

  useEffect(() => {
    const onScroll = () => {
      const height = document.documentElement.scrollHeight - window.innerHeight;
      const value = height <= 0 ? 1 : Math.min(1, Math.max(0, window.scrollY / height));
      setProgress(value);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  useEffect(() => {
    setLiked(window.localStorage.getItem(`varta-like:${articleId}`) === "1");
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, [articleId]);

  function toggleLike() {
    const next = !liked;
    setLiked(next);
    const key = `varta-like:${articleId}`;
    if (next) window.localStorage.setItem(key, "1");
    else window.localStorage.removeItem(key);
    setNote(next ? "Вподобання збережено на цьому пристрої." : "Вподобання прибрано.");
  }

  function toggleSpeech() {
    if (!window.speechSynthesis) {
      setNote("Озвучення недоступне в цьому браузері.");
      return;
    }
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      setNote("Відтворення зупинено.");
      return;
    }
    const text = [title, summary].filter(Boolean).join(". ");
    if (!text) {
      setNote("Для цього матеріалу немає тексту, який можна прослухати.");
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "uk-UA";
    utterance.rate = 0.98;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = (event) => {
      if (event.error === "interrupted" || event.error === "canceled") return;
      setSpeaking(false);
      setNote("Озвучення недоступне в цьому браузері.");
    };
    setSpeaking(true);
    setNote("Читаємо заголовок і короткий виклад.");
    window.speechSynthesis.cancel();
    // Chrome drops an utterance that starts in the same turn as cancel().
    window.setTimeout(() => {
      window.speechSynthesis.speak(utterance);
    }, 80);
  }

  async function share() {
    const url = window.location.href;
    const payload = { title, text: title, url };
    if (navigator.share) {
      try {
        await navigator.share(payload);
        setNote("Поділилися посиланням на матеріал.");
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setNote("Посилання скопійовано.");
      return;
    } catch {
      const field = document.createElement("textarea");
      field.value = url;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.left = "-9999px";
      document.body.append(field);
      field.select();
      const copied = document.execCommand("copy");
      field.remove();
      setNote(copied ? "Посилання скопійовано." : "Не вдалося скопіювати посилання.");
    }
  }

  return (
    <>
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[3px]"
        role="progressbar"
        aria-label="Прогрес читання"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress * 100)}
      >
        <div
          className="h-full w-full origin-left bg-zinc-950 dark:bg-white"
          style={{ transform: `scaleX(${progress})` }}
        />
      </div>
      <div className="pointer-events-none fixed bottom-5 left-1/2 z-40 flex -translate-x-1/2 flex-col items-center gap-2 px-4 xl:bottom-auto xl:left-8 xl:top-1/2 xl:translate-x-0 xl:-translate-y-1/2 xl:items-start">
        {note ? (
          <p className="max-w-[16rem] rounded-full border border-black/10 bg-zinc-950 px-3 py-1 text-xs text-white shadow-sm dark:border-white/10 dark:bg-white dark:text-zinc-950">
            {note}
          </p>
        ) : null}
        <div className="pointer-events-auto flex items-center gap-1 rounded-full border border-black/10 bg-[#f6f6f7]/75 p-1.5 shadow-[0_10px_40px_rgba(0,0,0,0.08)] backdrop-blur-[20px] xl:flex-col dark:border-white/10 dark:bg-[#0A0A0C]/75 dark:shadow-[0_10px_40px_rgba(0,0,0,0.45)]">
          <button type="button" className={control} onClick={toggleSpeech} aria-pressed={speaking}>
            <Volume2 size={16} strokeWidth={1.75} aria-hidden="true" />
            {speaking ? "Зупинити" : "Прослухати"}
          </button>
          <button type="button" className={control} onClick={() => void share()}>
            <Share2 size={16} strokeWidth={1.75} aria-hidden="true" />
            Поділитися
          </button>
          <button type="button" className={control} onClick={toggleLike} aria-pressed={liked}>
            <Heart
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className={liked ? "fill-current" : undefined}
            />
            {liked ? "Подобається" : "Вподобати"}
          </button>
        </div>
      </div>
      <p className="sr-only" aria-live="polite">
        {note}
      </p>
    </>
  );
}
