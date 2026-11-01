export const CATEGORIES = [
  {
    slug: "ukraina",
    label: "Україна",
    blurb: "Події в країні: міста, влада на місцях, економіка і суспільство.",
  },
  {
    slug: "viina",
    label: "Війна",
    blurb: "Фронт, обстріли, оборона і наслідки ударів.",
  },
  {
    slug: "polityka",
    label: "Політика",
    blurb: "Рішення влади, партії, переговори і внутрішні суперечки.",
  },
  {
    slug: "svit",
    label: "Світ",
    blurb: "Міжнародні новини, які змінюють контекст довкола України.",
  },
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];

export function getCategory(slug: string) {
  return CATEGORIES.find((category) => category.slug === slug);
}

export function categoryLabel(slug: CategorySlug): string {
  return getCategory(slug)?.label ?? slug;
}
