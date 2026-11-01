import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { dedupe } from "./text.ts";
import {
  classify,
  isOffTopic,
  makeId,
  normalizeTitle,
  titlesMatch,
  toExcerpt,
} from "./text.ts";
import type { NewsItem } from "./types.ts";

describe("excerpt", () => {
  it("strips html and decodes entities", () => {
    const text = toExcerpt("<p>Київ &amp; область</p><p>Друге речення.</p>");
    assert.equal(text, "Київ & область Друге речення.");
  });

  it("truncates long text without keeping the full article", () => {
    const text = toExcerpt(`${"довге речення ".repeat(40)}`);
    assert.ok(text.length <= 321);
    assert.ok(text.endsWith("…"));
  });
});

describe("classify", () => {
  it("sends an airstrike to the war section", () => {
    assert.equal(
      classify(
        "Російська армія авіаударом зруйнувала будівлю міськвиконкому в Краматорську",
        "",
        ["Новини"],
        "ukraina",
      ),
      "viina",
    );
  });

  it("sends a presidential meeting to politics", () => {
    assert.equal(
      classify("Зеленський зустрівся із Вселенським патріархом Варфоломієм", "", [], "ukraina"),
      "polityka",
    );
  });

  it("sends G20 diplomacy to the world section", () => {
    assert.equal(
      classify("Рубіо захистив запрошення Росії на зустрічі G20", "", ["Новини"], "ukraina"),
      "svit",
    );
  });

  it("keeps a domestic city story in Ukraine when there is no stronger signal", () => {
    assert.equal(
      classify("У Львові відкрили нову станцію сортування", "", ["Регіони"], "svit"),
      "ukraina",
    );
  });

  it("uses the feed fallback when the text has no signal", () => {
    assert.equal(classify("Коротке повідомлення редакції", "", [], "svit"), "svit");
  });

  it("keeps a frontline advance in the war section even when a city is named", () => {
    assert.equal(
      classify("DeepState: Війська РФ просунулись поблизу Миколаївки на Донеччині", "", [], "ukraina"),
      "viina",
    );
    assert.equal(
      classify(
        "Вибухи на Полтавщині і в Харкові",
        "У Києві та Дніпрі також є перебої зі світлом після ударів.",
        [],
        "ukraina",
      ),
      "viina",
    );
  });

  it("does not treat a criminal cyberattack as the war", () => {
    assert.equal(
      classify("ФБР заявило, що за атакою на Binance стоїть Північна Корея", "", [], "ukraina"),
      "svit",
    );
  });

  it("sends a Serbia capital-control story to the world section", () => {
    assert.equal(
      classify(
        "Сербський «Студентський список» закликав банки стежити за виведенням грошей із країни",
        "",
        ["Новини"],
        "ukraina",
      ),
      "svit",
    );
  });

  it("keeps a foreign military crisis in the world section", () => {
    assert.equal(
      classify(
        "Хаменеї наказав розширити плани ударів Ірану у відповідь на атаки США й Ізраїлю",
        "",
        ["Світ"],
        "ukraina",
      ),
      "svit",
    );
  });
});

describe("off topic", () => {
  it("drops astrology and TV roundups", () => {
    assert.equal(isOffTopic("Гороскоп на понеділок", ["Астрология"]), true);
    assert.equal(isOffTopic("Найкращі серіали листопада", []), true);
    assert.equal(isOffTopic("Україні прогнозують до +15°, подекуди дощі", ["Україна"]), true);
    assert.equal(isOffTopic("8 популярних техно-гаджетів цього року", ["Технології"]), true);
    assert.equal(isOffTopic("Перший продюсер Нікіток зізнався у старті кар'єри", []), true);
    assert.equal(
      isOffTopic("Залізні спортсмени. Олімпіада роботів-гуманоїдів у Пекіні", ["Світ"]),
      true,
    );
  });

  it("keeps a war story even if the category looks soft", () => {
    assert.equal(isOffTopic("Дрони вдарили по енергетиці Харкова", ["Технології"]), false);
  });
});

describe("dedupe", () => {
  it("merges obvious repeats and does not require a source url", () => {
    const older: NewsItem = {
      id: "old",
      title: "Трамп вважає, що мирна угода наближається!",
      summary: "Коротко.",
      source: "Укрінформ",
      publishedAt: "2026-10-31T10:00:00.000Z",
      category: "svit",
      image: "https://example.com/photo.jpg",
    };
    const newer: NewsItem = {
      id: "new",
      title: "Трамп вважає, що мирна угода наближається",
      summary: "Трохи довший виклад тієї самої події для картки.",
      source: "Європейська правда",
      publishedAt: "2026-10-31T12:00:00.000Z",
      category: "svit",
    };
    const other: NewsItem = {
      id: "other",
      title: "У Львові відкрили станцію",
      summary: "",
      source: "Українська правда",
      publishedAt: "2026-10-31T11:00:00.000Z",
      category: "ukraina",
    };

    const result = dedupe([older, newer, other]);
    assert.equal(result.length, 2);
    const merged = result.find((item) => item.title.startsWith("Трамп"));
    assert.ok(merged);
    assert.equal(merged?.source, "Європейська правда");
    assert.equal(merged?.image, "https://example.com/photo.jpg");
    assert.match(merged?.summary ?? "", /Трохи довший/);
    assert.equal("url" in (merged as NewsItem), false);
  });

  it("builds a stable id from the title alone", () => {
    assert.equal(makeId("Київ: тривога"), makeId("київ тривога"));
    assert.notEqual(normalizeTitle("А"), normalizeTitle("Б"));
    assert.equal(titlesMatch("Одна й та сама новина", "Зовсім інша історія"), false);
  });
});
