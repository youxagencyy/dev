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

export type ArticleCategoryCode = "UKRAINA" | "VIINA" | "POLITYKA" | "SVIT";

const TO_ENUM: Record<CategorySlug, ArticleCategoryCode> = {
  ukraina: "UKRAINA",
  viina: "VIINA",
  polityka: "POLITYKA",
  svit: "SVIT",
};

const FROM_ENUM: Record<ArticleCategoryCode, CategorySlug> = {
  UKRAINA: "ukraina",
  VIINA: "viina",
  POLITYKA: "polityka",
  SVIT: "svit",
};

export function categoryToEnum(slug: CategorySlug): ArticleCategoryCode {
  return TO_ENUM[slug];
}

export function categoryFromEnum(code: string): CategorySlug | null {
  if (code in FROM_ENUM) return FROM_ENUM[code as ArticleCategoryCode];
  return null;
}

export function selectedSlugs(codes: string[]): CategorySlug[] {
  return codes.flatMap((code) => {
    const slug = categoryFromEnum(code);
    return slug ? [slug] : [];
  });
}
