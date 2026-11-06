import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { shouldCheapRejectBot } from "./bot-guard";

const google =
  "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)";
const bing = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)";
const browser =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36";

describe("shouldCheapRejectBot", () => {
  it("rejects known junk bots on city and deal routes", () => {
    assert.equal(
      shouldCheapRejectBot("/us/new-york", "Mozilla/5.0 (compatible; AhrefsBot/7.0)"),
      true,
    );
    assert.equal(
      shouldCheapRejectBot(
        "/uk/london/deals/abc",
        "Mozilla/5.0 (compatible; SemrushBot/7~bl)",
      ),
      true,
    );
    assert.equal(shouldCheapRejectBot("/ie/dublin", "curl/8.4.0"), true);
    assert.equal(
      shouldCheapRejectBot("/us/chicago/deals/1", "python-requests/2.31.0"),
      true,
    );
  });

  it("lets search crawlers and browsers through", () => {
    assert.equal(shouldCheapRejectBot("/us/new-york", google), false);
    assert.equal(shouldCheapRejectBot("/uk/london/deals/abc", bing), false);
    assert.equal(
      shouldCheapRejectBot("/us/new-york", "AdsBot-Google (+http://www.google.com/adsbot.html)"),
      false,
    );
    assert.equal(shouldCheapRejectBot("/ie/dublin", browser), false);
    assert.equal(shouldCheapRejectBot("/us/new-york", ""), false);
    assert.equal(shouldCheapRejectBot("/us/new-york", null), false);
  });

  it("does not apply the cheap response outside deal and city routes", () => {
    assert.equal(shouldCheapRejectBot("/", "AhrefsBot/7.0"), false);
    assert.equal(shouldCheapRejectBot("/us", "AhrefsBot/7.0"), false);
    assert.equal(shouldCheapRejectBot("/about", "curl/8.4.0"), false);
    assert.equal(shouldCheapRejectBot("/newsletter", "SemrushBot/7"), false);
    assert.equal(shouldCheapRejectBot("/go/abc", "curl/8.4.0"), false);
  });
});
