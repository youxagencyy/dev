-- AlterEnum
ALTER TYPE "ArticleStatus" ADD VALUE 'DELETED';

-- AlterTable
ALTER TABLE "Source" ADD COLUMN "fallback" "ArticleCategory" NOT NULL DEFAULT 'UKRAINA';

-- Seed the public RSS set. ON CONFLICT keeps a source an editor already removed or edited.
INSERT INTO "Source" ("id", "name", "feedUrl", "active", "fallback", "createdAt", "updatedAt")
VALUES
  ('src_pravda', 'Українська правда', 'https://www.pravda.com.ua/rss/', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_ukrinform', 'Укрінформ', 'https://www.ukrinform.ua/rss/block-lastnews', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_bbc', 'BBC News Україна', 'https://feeds.bbci.co.uk/ukrainian/rss.xml', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_svoboda', 'Радіо Свобода', 'https://www.radiosvoboda.org/api/', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_nv', 'NV', 'https://nv.ua/ukr/rss/all.xml', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_euro', 'Європейська правда', 'https://www.eurointegration.com.ua/rss/', true, 'SVIT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_dw', 'DW', 'https://rss.dw.com/xml/rss-ukr-all', true, 'SVIT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
  ('src_unian', 'УНІАН', 'https://rss.unian.net/site/news_ukr.rss', true, 'UKRAINA', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT ("feedUrl") DO NOTHING;
