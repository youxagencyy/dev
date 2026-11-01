import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  filterStories,
  highlightParts,
  matchesQuery,
  parseSearchFilters,
  relatedStories,
  withinTime,
} from "./search.ts";
import type { NewsItem } from "./types.ts";

const NOW = Date.parse("2026-11-01T12:00:00.000Z");

function item(patch: Partial<NewsItem> & Pick<NewsItem, "id">): NewsItem {
  return {
    title: patch.title ?? patch.id,
    summary: patch.summary ?? "",
    source: patch.source ?? "Тест",
    publishedAt: patch.publishedAt ?? "2026-11-01T10:00:00.000Z",
    category: patch.category ?? "ukraina",
    tags: patch.tags ?? [],
    ...patch,
  };
}

describe("search", () => {
  const stories = [
    item({
      id: "kyiv",
      title: "У Києві відновили рух",
      summary: "Комунальні служби працюють.",
      category: "ukraina",
      tags: ["Київ"],
      publishedAt: "2026-11-01T09:00:00.000Z",
    }),
    item({
      id: "drones",
      title: "Дрони вдарили по енергетиці",
      summary: "Харків без світла.",
      category: "viina",
      tags: ["Дрони", "Харків", "Енергетика"],
      publishedAt: "2026-10-31T20:00:00.000Z",
    }),
    item({
      id: "old",
      title: "Стара нотатка про Польщу",
      category: "svit",
      tags: ["Польща"],
      publishedAt: "2026-10-20T12:00:00.000Z",
    }),
  ];

  it("matches every token in the title, summary, or tag", () => {
    assert.equal(matchesQuery(stories[0], "києві служби"), true);
    assert.equal(matchesQuery(stories[0], "Київ"), true);
    assert.equal(matchesQuery(item({ id: "noise", title: "Дональд на кордоні" }), "дрон"), false);
    assert.equal(matchesQuery(stories[0], "києві дрони"), false);
    assert.equal(matchesQuery(stories[1], "харків"), true);
  });

  it("filters by category, tag, and Kyiv time together", () => {
    assert.equal(withinTime("2026-10-31T22:30:00.000Z", "today", NOW), true);
    assert.equal(withinTime("2026-10-31T20:00:00.000Z", "today", NOW), false);
    assert.equal(withinTime("2026-10-31T20:00:00.000Z", "day", NOW), true);
    assert.equal(withinTime("2026-10-30T10:00:00.000Z", "day", NOW), false);

    const found = filterStories(
      stories,
      { query: "", category: "viina", tag: "Дрони", time: "week" },
      NOW,
    );
    assert.deepEqual(found.map((entry) => entry.id), ["drones"]);

    const today = filterStories(stories, { query: "київ", category: "all", tag: "", time: "today" }, NOW);
    assert.deepEqual(today.map((entry) => entry.id), ["kyiv"]);
  });

  it("highlights an inflected Kyiv mention", () => {
    const parts = highlightParts("Зеленський у Києві", "Київ");
    assert.equal(parts.map((part) => part.text).join(""), "Зеленський у Києві");
    assert.deepEqual(
      parts.filter((part) => part.hit).map((part) => part.text),
      ["Києві"],
    );
  });

  it("rejects unknown filter values", () => {
    assert.deepEqual(parseSearchFilters({ q: "  Київ  ", category: "nope", time: "month", tag: "Фронт" }), {
      query: "Київ",
      category: "all",
      tag: "Фронт",
      time: "all",
    });
  });

  it("prefers shared tags, then fills the rest", () => {
    const current = item({
      id: "current",
      category: "viina",
      tags: ["Дрони", "Харків"],
      publishedAt: "2026-11-01T11:00:00.000Z",
    });
    const tagged = item({
      id: "tagged",
      category: "svit",
      tags: ["Дрони", "Харків"],
      publishedAt: "2026-11-01T08:00:00.000Z",
    });
    const same = item({
      id: "same",
      category: "viina",
      tags: [],
      publishedAt: "2026-11-01T10:00:00.000Z",
    });
    const other = item({
      id: "other",
      category: "polityka",
      tags: [],
      publishedAt: "2026-11-01T07:00:00.000Z",
    });
    const related = relatedStories(current, [current, other, same, tagged], 3);
    assert.deepEqual(related.map((entry) => entry.id), ["tagged", "same", "other"]);
  });
});
