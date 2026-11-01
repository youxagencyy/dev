# ВАРТА

Публічний агрегатор новин українською. На головній — свіжа стрічка, окремо розділи **Україна**, **Війна**, **Політика** і **Світ**.

Картка й сторінка матеріалу показують заголовок, короткий виклад і назву редакції. Повні тексти не копіюються: у стрічці лише те, що видання вже віддає у відкритому RSS.

## Запуск

Потрібен Node.js 22+.

```bash
npm install && npm run dev
```

Відкрийте [http://localhost:3000](http://localhost:3000).

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

## English

Public Ukrainian-language news digest. One command after Node 22:

```bash
npm install && npm run dev
```

Open http://localhost:3000. Headlines and short RSS excerpts only, cached for 10 minutes. A failed feed is skipped.
