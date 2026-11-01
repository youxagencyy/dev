# ВАРТА

Публічний агрегатор новин українською. На головній — свіжа стрічка, окремо розділи **Україна**, **Війна**, **Політика** і **Світ**.

Картка й сторінка матеріалу показують заголовок, короткий виклад і назву редакції. Повні тексти не копіюються: у стрічці лише те, що видання вже віддає у відкритому RSS.

## Запуск

Потрібен Node.js 22+.

```bash
npm install && npm run dev
```

Відкрийте [http://localhost:3000](http://localhost:3000). Пошук — на `/search`. На сторінці матеріалу — прогрес читання, поширення посилання ВАРТИ і кнопка «Прослухати» через озвучення браузера. Посилання на сайт редакції не додається: достатньо назви видання.

На сайті видно лише опубліковані матеріали. Нові записи з RSS спершу падають у чергу редакції як чернетки.

Кабінет читача: реєстрація на `/reiestratsiia`, вхід на `/uviity`. Там теми закладок, історія читання і налаштування теми, стрічки та сповіщень. Для кабінету потрібні Postgres і `AUTH_SECRET` у `.env`.

Редакція — на `/redaktsiia`. Туди пускає лише роль admin. Читач бачить відмову. Черга має «Опублікувати» і «Видалити». Джерела можна додати, вимкнути й прибрати. Якщо під час збору джерело не відповідає, уже опублікована стрічка лишається.

Ключ API не потрібен. Перепис текстів не вмикається.

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

У схемі: джерела, матеріали зі статусами чернетка / опубліковано / видалено, користувачі з ролями reader/admin, пароль для локального входу, тема, розділи персональної стрічки, моделі NextAuth, закладки й теки, історія читання, налаштування сповіщень.

Локального редактора створює `npm run admin:seed`, якщо в оточенні задані `ADMIN_EMAIL` і `ADMIN_PASSWORD`. Пароль у інтерфейс не виводиться.

Той самий `DATABASE_URL` працює і з локальним PostgreSQL на порту 5432, без Docker.

## English

Public Ukrainian-language news digest. One command after Node 22:

```bash
npm install && npm run dev
```

Open http://localhost:3000. Headlines and short RSS excerpts only, cached for 10 minutes. A failed feed is skipped. Search lives at `/search`. Article pages can be read aloud with the browser Speech Synthesis API.

The public homepage lists published stories from Postgres. Ingested RSS items wait as drafts in `/redaktsiia`, which only an admin can open. A failed feed leaves published stories in place. Copy `.env.example` to `.env`, set `AUTH_SECRET`, start PostgreSQL on port 5432, then run `npx prisma migrate deploy`. Sign up at `/reiestratsiia`. New accounts are readers. Create an editor with `ADMIN_EMAIL` and `ADMIN_PASSWORD` via `npm run admin:seed`. Theme, bookmarks, read history, and notification toggles are stored in the database. There is no rewrite pipeline.
