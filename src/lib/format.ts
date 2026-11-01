const KYIV = "Europe/Kyiv";

export function formatToday(now = new Date()): string {
  const formatted = new Intl.DateTimeFormat("uk-UA", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: KYIV,
  }).format(now);
  return formatted.charAt(0).toLocaleUpperCase("uk") + formatted.slice(1);
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("uk-UA", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: KYIV,
  }).format(date);
}

export function formatClock(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("uk-UA", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: KYIV,
  }).format(date);
}

function plural(count: number, one: string, few: string, many: string): string {
  const abs = Math.abs(count);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function formatWhen(iso: string, now = Date.now()): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "";
  const diff = Math.max(0, now - time);
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 5) return "щойно";
  if (minutes < 60) {
    return `${minutes} ${plural(minutes, "хвилину", "хвилини", "хвилин")} тому`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} ${plural(hours, "годину", "години", "годин")} тому`;
  }
  const days = Math.floor(hours / 24);
  if (days === 1) return "учора";
  if (days < 7) return `${days} ${plural(days, "день", "дні", "днів")} тому`;
  return formatDateTime(iso);
}

export function formatCount(count: number): string {
  return `${count} ${plural(count, "матеріал", "матеріали", "матеріалів")}`;
}
