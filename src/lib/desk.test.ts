import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { incomingStatus, parseFeedUrl, parseSourceName } from "./desk.ts";

describe("editorial desk", () => {
  it("keeps published and deleted stories out of the draft queue", () => {
    assert.equal(incomingStatus(null), "create");
    assert.equal(incomingStatus("DRAFT"), "refresh");
    assert.equal(incomingStatus("PUBLISHED"), "leave");
    assert.equal(incomingStatus("DELETED"), "leave");
  });

  it("accepts an http feed address and a short name", () => {
    assert.equal(parseFeedUrl("https://example.com/rss"), "https://example.com/rss");
    assert.equal(parseFeedUrl("ftp://example.com/rss"), null);
    assert.equal(parseFeedUrl("not a url"), null);
    assert.equal(parseSourceName("  NV  "), "NV");
    assert.equal(parseSourceName("a"), null);
  });
});
