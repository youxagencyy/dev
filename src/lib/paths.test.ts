import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { categoryFromEnum, categoryToEnum } from "./categories.ts";
import { safeNext } from "./paths.ts";
import { parseTheme } from "./theme.ts";

describe("reader paths and settings", () => {
  it("keeps internal return paths and drops external ones", () => {
    assert.equal(safeNext("/n/abc"), "/n/abc");
    assert.equal(safeNext("https://example.com"), "/kabinet");
    assert.equal(safeNext("//example.com"), "/kabinet");
    assert.equal(safeNext(null), "/kabinet");
  });

  it("maps sections both ways", () => {
    assert.equal(categoryToEnum("viina"), "VIINA");
    assert.equal(categoryFromEnum("SVIT"), "svit");
    assert.equal(categoryFromEnum("nope"), null);
  });

  it("accepts only the three themes", () => {
    assert.equal(parseTheme("DARK"), "DARK");
    assert.equal(parseTheme("blue"), "SYSTEM");
  });
});
