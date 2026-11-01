import type { CategorySlug } from "./categories";

export type NewsItem = {
  id: string;
  title: string;
  summary: string;
  source: string;
  publishedAt: string;
  category: CategorySlug;
  tags: string[];
  image?: string;
};

export type FeedFailure = {
  source: string;
  reason: string;
};

export type NewsSnapshot = {
  items: NewsItem[];
  fetchedAt: string;
  failures: FeedFailure[];
  sources: string[];
};
