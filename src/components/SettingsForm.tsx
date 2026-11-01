"use client";

import { useState } from "react";
import { saveSettingsAction } from "@/app/kabinet/actions";
import { CATEGORIES, type CategorySlug } from "@/lib/categories";
import { THEMES, applyTheme, type ThemeChoice } from "@/lib/theme";

const choice =
  "rounded-full border px-3 py-1.5 text-[13px] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:focus-visible:outline-white";

export function SettingsForm({
  theme,
  feed,
  notify,
  breaking,
  dailyBrief,
  emailEnabled,
  saved,
  error,
}: {
  theme: ThemeChoice;
  feed: CategorySlug[];
  notify: CategorySlug[];
  breaking: boolean;
  dailyBrief: boolean;
  emailEnabled: boolean;
  saved: boolean;
  error: string | null;
}) {
  const [currentTheme, setCurrentTheme] = useState(theme);

  function chooseTheme(next: ThemeChoice, form: HTMLFormElement) {
    const input = form.elements.namedItem("theme");
    if (input instanceof HTMLInputElement) input.value = next;
    setCurrentTheme(next);
    applyTheme(next);
    form.requestSubmit();
  }

  return (
    <form action={saveSettingsAction} className="space-y-10">
      <input type="hidden" name="theme" value={currentTheme} />
      <fieldset>
        <legend className="text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">Тема</legend>
        <div className="mt-3 flex flex-wrap gap-2">
          {THEMES.map((entry) => {
            const pressed = currentTheme === entry.id;
            return (
              <button
                key={entry.id}
                type="button"
                aria-pressed={pressed}
                onClick={(event) => {
                  const form = event.currentTarget.form;
                  if (form) chooseTheme(entry.id, form);
                }}
                className={`${choice} ${
                  pressed
                    ? "border-transparent bg-zinc-950 text-white dark:bg-white dark:text-zinc-950"
                    : "border-black/10 text-zinc-600 dark:border-white/10 dark:text-zinc-300"
                }`}
              >
                {entry.label}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-sm text-zinc-500">Тема змінює весь сайт і зберігається в обліковому записі.</p>
      </fieldset>

      <CheckGroup
        legend="Моя стрічка"
        hint="Розділи, які залишаються у персональній стрічці кабінету."
        name="feed"
        selected={feed}
      />
      <fieldset className="space-y-3">
        <legend className="text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">Сповіщення</legend>
        <Toggle name="breaking" label="Термінові сповіщення" defaultChecked={breaking} />
        <Toggle name="dailyBrief" label="Щоденний бриф" defaultChecked={dailyBrief} />
        <Toggle name="emailEnabled" label="Листи на пошту" defaultChecked={emailEnabled} />
      </fieldset>
      <CheckGroup
        legend="Розділи для сповіщень"
        hint="Про які розділи нагадувати, коли сповіщення увімкнені."
        name="note"
        selected={notify}
      />

      {error === "feed" ? (
        <p className="text-sm text-zinc-700 dark:text-zinc-200">Залиште бодай один розділ у моїй стрічці.</p>
      ) : null}
      {saved ? <p className="text-sm text-zinc-500">Налаштування збережено.</p> : null}
      <button
        type="submit"
        className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm text-white dark:bg-white dark:text-zinc-950"
      >
        Зберегти
      </button>
    </form>
  );
}

function CheckGroup({
  legend,
  hint,
  name,
  selected,
}: {
  legend: string;
  hint: string;
  name: string;
  selected: CategorySlug[];
}) {
  return (
    <fieldset>
      <legend className="text-[11px] font-medium tracking-[0.16em] text-zinc-400 uppercase">{legend}</legend>
      <p className="mt-2 text-sm text-zinc-500">{hint}</p>
      <div className="mt-3 flex flex-wrap gap-3">
        {CATEGORIES.map((category) => (
          <label key={category.slug} className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              name={`${name}-${category.slug}`}
              defaultChecked={selected.includes(category.slug)}
              className="size-4 accent-zinc-950 dark:accent-white"
            />
            {category.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function Toggle({ name, label, defaultChecked }: { name: string; label: string; defaultChecked: boolean }) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-2xl border border-black/10 px-4 py-3 text-sm dark:border-white/10">
      {label}
      <input type="checkbox" name={name} defaultChecked={defaultChecked} className="size-4 accent-zinc-950 dark:accent-white" />
    </label>
  );
}
