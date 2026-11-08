import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { missingDealOrThrow } from "./deal-fetch-outcome.ts";

describe("missingDealOrThrow", () => {
  it("treats only HTTP 404 as a missing deal", () => {
    assert.doesNotThrow(() =>
      missingDealOrThrow(
        { ok: false, error: "Deal not found", status: 404 },
        "metadata",
      ),
    );
    assert.doesNotThrow(() =>
      missingDealOrThrow(
        { ok: false, error: "Deal not found", status: 404 },
        "page",
      ),
    );
  });

  it("throws on 5xx, other statuses, and network failures with no status", () => {
    assert.throws(
      () =>
        missingDealOrThrow(
          { ok: false, error: "upstream 503", status: 503 },
          "metadata",
        ),
      /fetchDeal failed for metadata: upstream 503/,
    );
    assert.throws(
      () =>
        missingDealOrThrow(
          { ok: false, error: "timeout", status: 500 },
          "page",
        ),
      /fetchDeal failed for page: timeout/,
    );
    assert.throws(
      () =>
        missingDealOrThrow({ ok: false, error: "fetch failed" }, "metadata"),
      /fetchDeal failed for metadata: fetch failed/,
    );
  });
});

describe("deal page wiring", () => {
  const source = readFileSync(
    join(
      dirname(fileURLToPath(import.meta.url)),
      "../app/[country]/[city]/deals/[id]/page.tsx",
    ),
    "utf8",
  );

  it("noindexes a missing deal and throws for any other fetch failure", () => {
    assert.match(source, /missingDealOrThrow\(result, "metadata"\)/);
    assert.match(source, /missingDealOrThrow\(result, "page"\)/);
    assert.match(source, /notFound\(\)/);
    assert.doesNotMatch(source, /if \(!result\.ok \|\| isPlaceholderCitySlug/);
  });

  it("still noindexes placeholder city slugs", () => {
    assert.match(source, /isPlaceholderCitySlug\(params\.city\)/);
    assert.match(source, /isPlaceholderCitySlug\(result\.data\.city\)/);
  });
});
