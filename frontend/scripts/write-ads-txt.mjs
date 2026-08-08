/**
 * Writes public/ads.txt from NEXT_PUBLIC_ADSENSE_PUBLISHER_ID (or CLIENT).
 * Run during `npm run build` so production always serves a crawlable ads.txt.
 */
import { writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const out = join(root, "public", "ads.txt");

const raw =
  process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID?.trim() ||
  process.env.NEXT_PUBLIC_ADSENSE_CLIENT?.trim() ||
  "";

const publisher = raw.replace(/^ca-/, "");

if (!/^pub-\d{16}$/.test(publisher)) {
  const placeholder = [
    "# AdSense ads.txt — set NEXT_PUBLIC_ADSENSE_PUBLISHER_ID=pub-XXXXXXXXXXXXXXXX",
    "# then rebuild. Format:",
    "# google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0",
    "",
  ].join("\n");
  writeFileSync(out, placeholder, "utf8");
  console.warn(
    "[write-ads-txt] No valid publisher ID — wrote placeholder ads.txt",
  );
  process.exit(0);
}

const body = [
  `# Dine A Deal — Authorized Digital Sellers`,
  `google.com, ${publisher}, DIRECT, f08c47fec0942fa0`,
  "",
].join("\n");

writeFileSync(out, body, "utf8");
console.log(`[write-ads-txt] Wrote ads.txt for ${publisher}`);
