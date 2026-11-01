import type { CategorySlug } from "./categories";

export type FeedSource = {
  name: string;
  url: string;
  fallback: CategorySlug;
};

/** Public RSS feeds. Items stay short excerpts with the outlet name as attribution. */
export const FEEDS: FeedSource[] = [
  {
    name: "Українська правда",
    url: "https://www.pravda.com.ua/rss/",
    fallback: "ukraina",
  },
  {
    name: "Укрінформ",
    url: "https://www.ukrinform.ua/rss/block-lastnews",
    fallback: "ukraina",
  },
  {
    name: "BBC News Україна",
    url: "https://feeds.bbci.co.uk/ukrainian/rss.xml",
    fallback: "ukraina",
  },
  {
    name: "Радіо Свобода",
    url: "https://www.radiosvoboda.org/api/",
    fallback: "ukraina",
  },
  {
    name: "NV",
    url: "https://nv.ua/ukr/rss/all.xml",
    fallback: "ukraina",
  },
  {
    name: "Європейська правда",
    url: "https://www.eurointegration.com.ua/rss/",
    fallback: "svit",
  },
  {
    name: "DW",
    url: "https://rss.dw.com/xml/rss-ukr-all",
    fallback: "svit",
  },
  {
    name: "УНІАН",
    url: "https://rss.unian.net/site/news_ukr.rss",
    fallback: "ukraina",
  },
];
