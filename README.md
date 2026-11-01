# ВАРТА

Публічний агрегатор новин українською. На головній — свіжа стрічка, окремо розділи **Україна**, **Війна**, **Політика** і **Світ**.

Картка й сторінка матеріалу показують заголовок, короткий виклад і назву редакції. Повні тексти не копіюються: у стрічці лише те, що видання вже віддає у відкритому RSS.

## Запуск

Потрібен Node.js 22+.

```bash
npm install && npm run dev
```

Відкрийте [http://localhost:3000](http://localhost:3000). Пошук — на `/search`: збіги підсвічуються одразу, є фільтри розділу, тега й часу. На сторінці матеріалу — прогрес читання, вподобання на цьому пристрої, поширення посилання ВАРТИ і кнопка «Прослухати» через озвучення браузера. Посилання на сайт редакції не додається: достатньо назви видання.

Стрічки читаються на сервері й кешуються на 10 хвилин. Ключ API не потрібен. Якщо якесь джерело не відповідає, сайт показує решту.

Інші команди:

```bash
npm test
npm run build
npm start
```

## Джерела

- Українська правда — `https://www.pravda.com.ua/rss/`
- Укрінформ — `https://www.ukrinform.ua/rss/block-lastnews`
- BBC News Україна — `https://feeds.bbci.co.uk/ukrainian/rss.xml`
- Радіо Свобода — `https://www.radiosvoboda.org/api/`
- NV — `https://nv.ua/ukr/rss/all.xml`
- Європейська правда — `https://www.eurointegration.com.ua/rss/`
- DW — `https://rss.dw.com/xml/rss-ukr-all`
- УНІАН — `https://rss.unian.net/site/news_ukr.rss`

## Локальний Postgres

Головна не чекає на базу: стрічка збирається з RSS. Схема Prisma і міграція вже в репозиторії. Коли з’явиться Postgres:

```bash
docker run --name varta-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=varta \
  -p 5432:5432 \
  -d postgres:16

cp .env.example .env
npx prisma migrate deploy
```

`DATABASE_URL` у `.env.example`: `postgresql://postgres:postgres@localhost:5432/varta?schema=public`.

У схемі: джерела, матеріали (заголовок, переписаний текст, три пункти викладу, теги, обкладинка, розділ, статус чернетка/опубліковано), користувачі з ролями reader/admin, моделі NextAuth, закладки й теки, історія читання, налаштування сповіщень. Вхід, кабінет і перепис текстів у цьому кроці не вмикаються.

## English

Public Ukrainian-language news digest. One command after Node 22:

```bash
npm install && npm run dev
```

Open http://localhost:3000. Headlines and short RSS excerpts only, cached for 10 minutes. A failed feed is skipped. Search lives at `/search`. Article pages can be read aloud with the browser Speech Synthesis API.

Postgres is optional for the homepage. Schema and migration: `prisma/schema.prisma`, `prisma/migrations/20261101130000_init`. Apply with `npx prisma migrate deploy` after copying `.env.example` to `.env` and starting a local database on port 5432.
