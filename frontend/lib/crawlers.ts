/**
 * Known search / ads crawlers. Used to skip newsletter overlays so
 * listing HTML stays visible to Googlebot and AdSense review bots.
 * Keep this list specific — do not match a generic "bot" substring.
 */
const CRAWLER_UA =
  /\b(Googlebot|Googlebot-Image|Googlebot-News|AdsBot-Google|AdsBot-Google-Mobile|Mediapartners-Google|Google-InspectionTool|Storebot-Google|Google-Safety|APIs-Google|Feedfetcher-Google|Bingbot|adidxbot|MicrosoftPreview|Slurp|DuckDuckBot|DuckAssistBot|facebookexternalhit|Facebot|Twitterbot|LinkedInBot|Applebot|YandexBot|YandexImages|Baiduspider|GPTBot|ChatGPT-User|ClaudeBot|Anthropic-AI|CCBot)\b/i;

export function isAdCrawler(userAgent: string | null | undefined): boolean {
  if (!userAgent?.trim()) return false;
  return CRAWLER_UA.test(userAgent);
}
