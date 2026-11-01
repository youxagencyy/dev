import { createHash } from "node:crypto";
import type { CategorySlug } from "./categories";
import type { NewsItem } from "./types";

const WHOLE_WORD = new Set([
  "ппо",
  "бпла",
  "зсу",
  "всу",
  "єс",
  "сша",
  "оон",
  "g20",
  "g7",
  "рада",
  "крим",
  "суми",
  "рф",
]);

const WAR_STEMS = [
  "війн",
  "фронт",
  "обстріл",
  "дрон",
  "ракет",
  "окупа",
  "артилер",
  "генштаб",
  "авіаудар",
  "влучан",
  "прильот",
  "міноборон",
  "зеніт",
  "снаряд",
  "бомб",
  "вибух",
  "збро",
  "шахед",
  "мобіліз",
  "блекаут",
  "енергосистем",
  "удар",
  "атаку",
  "військ",
  "просунул",
  "безпілот",
  "deepstate",
  "росіян",
  "ппо",
  "бпла",
  "зсу",
  "всу",
];

const POLITICS_STEMS = [
  "зеленськ",
  "президент",
  "верховн",
  "уряд",
  "міністр",
  "депутат",
  "парті",
  "вибор",
  "санкц",
  "парламент",
  "кабмін",
  "корупц",
  "голосуван",
  "опозиц",
  "закон",
  "політик",
  "політич",
  "переговор",
  "нардеп",
  "рада",
];

const WORLD_STEMS = [
  "трамп",
  "байден",
  "рубіо",
  "макрон",
  "нато",
  "євросоюз",
  "єврокоміс",
  "брюссел",
  "вашингтон",
  "німеччин",
  "франці",
  "францу",
  "британі",
  "китай",
  "пекін",
  "іран",
  "ізраїл",
  "палестин",
  "японі",
  "кореї",
  "корея",
  "польщ",
  "орбан",
  "кремл",
  "путін",
  "білий дім",
  "g20",
  "g7",
  "оон",
  "єс",
  "сша",
  "фбр",
  "іспані",
  "аргентин",
  "туреч",
  "ердоган",
  "албан",
  "фінлянд",
  "литв",
  "молдов",
  "білорус",
  "єгипет",
  "серб",
  "болгар",
  "румун",
  "угорщ",
];

const UKRAINE_STEMS = [
  "київ",
  "києв",
  "львов",
  "львів",
  "одес",
  "харків",
  "харков",
  "дніпр",
  "запоріж",
  "миколаїв",
  "миколаєв",
  "черніг",
  "полтав",
  "вінниц",
  "сумськ",
  "суми",
  "житомир",
  "черкас",
  "кропивниц",
  "хмельниц",
  "терноп",
  "закарпат",
  "буковин",
  "рівнен",
  "рівне",
  "волин",
  "гривн",
  "укрзалізн",
  "нафтогаз",
  "краматорськ",
  "словянськ",
  "покровськ",
  "херсон",
  "крим",
  "маріупол",
  "бахмут",
  "авдіїв",
];

export function fold(value: string): string {
  return value
    .toLocaleLowerCase("uk")
    .replace(/[’'`´ʼ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function normalizeTitle(title: string): string {
  return fold(title)
    .replace(/[^\p{L}\p{N}\s]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function makeId(title: string): string {
  return createHash("sha1").update(normalizeTitle(title)).digest("hex").slice(0, 12);
}

function hit(haystack: string, stem: string): boolean {
  if (WHOLE_WORD.has(stem)) {
    const escaped = stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(?:^|[^\\p{L}\\p{N}])${escaped}(?:$|[^\\p{L}\\p{N}])`, "iu").test(haystack);
  }
  return haystack.includes(stem);
}

function score(haystack: string, stems: string[]): number {
  let total = 0;
  for (const stem of stems) {
    if (hit(haystack, stem)) total += 1;
  }
  return total;
}

export function hintFromCategories(categories: string[]): CategorySlug | null {
  const blob = fold(categories.join(" | "));
  if (/війн|войн|оруж/.test(blob)) return "viina";
  if (/політик/.test(blob)) return "polityka";
  if (/(^|[|/\s])(світ|міжнарод\p{L}*|геополіт\p{L}*|мир)(?=$|[|/\s])/u.test(blob)) return "svit";
  if (/україн|регіон|суспіль|економ|енерг/.test(blob)) return "ukraina";
  return null;
}

function pickCategory(haystack: string): CategorySlug | null {
  const war = score(haystack, WAR_STEMS);
  const politics = score(haystack, POLITICS_STEMS);
  const world = score(haystack, WORLD_STEMS);
  const ukraine = score(haystack, UKRAINE_STEMS);
  if (war > 0 && world > war && politics === 0 && ukraine === 0) return "svit";
  if (war > 0) return "viina";
  if (politics > 0 || world > 0) return politics >= world ? "polityka" : "svit";
  if (ukraine > 0) return "ukraina";
  return null;
}

export function classify(
  title: string,
  summary: string,
  categories: string[],
  fallback: CategorySlug,
): CategorySlug {
  return (
    pickCategory(fold(title)) ??
    pickCategory(fold(summary)) ??
    hintFromCategories(categories) ??
    fallback
  );
}

const JUNK_TITLE =
  /астролог|гороскоп|рецепт|кулінар|знаменит|шоу-біз|що подивит|серіал|метеорит|синоптик|прогнозують до|дощ|гаджет|hdmi|смартфон|wi-fi|привид|параліч|світляч|хокей|гуманоїд|спортсмен|вбранн|концерт|орли|продюсер|нікіток|тікток|tiktok|інстаграм|instagram/;

export function isOffTopic(title: string, categories: string[]): boolean {
  const titleHay = fold(title);
  const categoryBlob = fold(categories.join(" "));
  const junkTitle = JUNK_TITLE.test(titleHay);
  const junkCategory =
    /астролог|гороскоп|здоров|цікавин|интересн|спорт|life|шоу|кулінар|знаменит|гаджет/.test(categoryBlob);
  const softCategory = /спорт|life|техно|бізнес|авто|стиль|знаменит/.test(categoryBlob);
  if (!junkTitle && !junkCategory && !softCategory) return false;

  if (junkTitle) {
    const keep = score(titleHay, WAR_STEMS) + score(titleHay, POLITICS_STEMS);
    return keep === 0;
  }

  const keep =
    score(titleHay, WAR_STEMS) + score(titleHay, POLITICS_STEMS) + score(titleHay, WORLD_STEMS);
  return keep === 0;
}

export function stripHtml(value: string): string {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<\/p>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#0?39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#x([0-9a-f]+);/gi, (_, hex: string) => fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec: string) => fromCodePoint(Number.parseInt(dec, 10)))
    .replace(/\s+/g, " ")
    .trim();
}

function fromCodePoint(code: number): string {
  if (!Number.isFinite(code) || code <= 0 || code > 0x10ffff) return "";
  try {
    return String.fromCodePoint(code);
  } catch {
    return "";
  }
}

export function toExcerpt(value: string | undefined, max = 320): string {
  const text = stripHtml(value ?? "");
  if (!text) return "";
  if (text.length <= max) return text;
  const slice = text.slice(0, max + 1);
  const space = slice.lastIndexOf(" ");
  const base = (space > max * 0.6 ? slice.slice(0, space) : text.slice(0, max)).trim();
  return `${base.replace(/[.,;:–—\-–\s]+$/u, "")}…`;
}

export function titlesMatch(left: string, right: string): boolean {
  const a = normalizeTitle(left);
  const b = normalizeTitle(right);
  if (!a || !b) return false;
  if (a === b) return true;

  const tokensA = significantTokens(a);
  const tokensB = significantTokens(b);
  if (tokensA.length < 5 || tokensB.length < 5) return false;

  const setB = new Set(tokensB);
  let intersection = 0;
  for (const token of new Set(tokensA)) {
    if (setB.has(token)) intersection += 1;
  }
  const union = new Set([...tokensA, ...tokensB]).size;
  return union > 0 && intersection / union >= 0.8;
}

function significantTokens(value: string): string[] {
  return value.split(" ").filter((token) => token.length >= 4);
}

const TOPIC_TAGS: { label: string; stems: string[] }[] = [
  { label: "Київ", stems: ["київ", "києв"] },
  { label: "Харків", stems: ["харків", "харков"] },
  { label: "Одеса", stems: ["одес"] },
  { label: "Зеленський", stems: ["зеленськ"] },
  { label: "Фронт", stems: ["фронт", "зсу"] },
  { label: "Дрони", stems: ["дрон", "бпла", "шахед"] },
  { label: "Енергетика", stems: ["енерг", "світл", "дтек"] },
  { label: "США", stems: ["сша", "трамп", "рубіо", "вашингтон"] },
  { label: "Європа", stems: ["європ", "брюссел", "єс"] },
  { label: "G20", stems: ["g20"] },
  { label: "Польща", stems: ["польщ", "туск"] },
  { label: "Переговори", stems: ["переговор", "мирн"] },
];

function stemHit(haystack: string, stem: string): boolean {
  if (stem.length <= 3) {
    const escaped = stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(?:^|[^\\p{L}\\p{N}])${escaped}(?:$|[^\\p{L}\\p{N}])`, "iu").test(haystack);
  }
  return haystack.includes(stem);
}

export function extractTags(title: string, summary: string): string[] {
  const haystack = fold(`${title} ${summary}`);
  const tags: string[] = [];
  for (const topic of TOPIC_TAGS) {
    if (!topic.stems.some((stem) => stemHit(haystack, stem))) continue;
    tags.push(topic.label);
    if (tags.length === 3) break;
  }
  return tags;
}

export function dedupe(items: NewsItem[]): NewsItem[] {
  const sorted = [...items].sort(
    (a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt),
  );
  const kept: NewsItem[] = [];

  for (const item of sorted) {
    const index = kept.findIndex((existing) => titlesMatch(existing.title, item.title));
    if (index === -1) {
      kept.push(item);
      continue;
    }
    const previous = kept[index];
    kept[index] = {
      ...previous,
      image: previous.image || item.image,
      summary: previous.summary.length >= item.summary.length ? previous.summary : item.summary,
      tags: [...new Set([...(previous.tags ?? []), ...(item.tags ?? [])])].slice(0, 4),
    };
  }

  return kept;
}

const MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;
const MAX_FUTURE_MS = 48 * 60 * 60 * 1000;

export function isFresh(iso: string, now = Date.now()): boolean {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return false;
  if (time - now > MAX_FUTURE_MS) return false;
  if (now - time > MAX_AGE_MS) return false;
  return true;
}
