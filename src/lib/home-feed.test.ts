import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { pickBrief } from "./home-feed.ts";
import type { NewsItem } from "./types.ts";

function item(id: string, category: NewsItem["category"], publishedAt: string): NewsItem {
  return {
    id,
    title: id,
    summary: "",
    source: "Тест",
    publishedAt,
    category,
  };
}

describe("pickBrief", () => {
  it("covers more than one section and stays at five items", () => {
    const items = [
      item("a", "viina", "2026-11-01T12:00:00.000Z"),
      item("b", "viina", "2026-11-01T11:00:00.000Z"),
      item("c", "svit", "2026-11-01T10:00:00.000Z"),
      item("d", "ukraina", "2026-11-01T09:00:00.000Z"),
      item("e", "polityka", "2026-11-01T08:00:00.000Z"),
      item("f", "svit", "2026-11-01T07:00:00.000Z"),
    ];
    const brief = pickBrief(items);
    assert.equal(brief.length, 5);
    assert.equal(new Set(brief.map((entry) => entry.category)).size >= 4, true);
    assert.ok(brief[0] && Date.parse(brief[0].publishedAt) >= Date.parse(brief[brief.length - 1].publishedAt));
  });
});
