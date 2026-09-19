import type { Metadata } from "next";
import { Crimson_Text, Oswald } from "next/font/google";
import { headers } from "next/headers";
import { AdSenseScript } from "@/components/ads/AdSenseScript";
import { VercelAnalytics } from "@/components/analytics/VercelAnalytics";
import { CookieConsentProvider } from "@/components/cookie/CookieConsentProvider";
import { ConditionalSiteHeader } from "@/components/landing/ConditionalSiteHeader";
import { ScrollToTopButton } from "@/components/landing/ScrollToTopButton";
import { SiteHeader } from "@/components/landing/SiteHeader";
import { NewsletterPopup } from "@/components/newsletter/NewsletterPopup";
import { getAdSenseClientId, isAdSenseConfigured } from "@/lib/adsense";
import { BRAND_NAME, BRAND_TAGLINE } from "@/lib/brand";
import { isAdCrawler } from "@/lib/crawlers";
import { HOME_DESCRIPTION } from "@/lib/seo";
import "./globals.css";

const oswald = Oswald({
  subsets: ["latin"],
  variable: "--font-oswald",
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const crimson = Crimson_Text({
  subsets: ["latin"],
  variable: "--font-crimson",
  weight: ["400", "600", "700"],
  display: "swap",
});

const adsenseClient =
  isAdSenseConfigured() ? getAdSenseClientId() : undefined;

export const metadata: Metadata = {
  title: {
    default: `${BRAND_NAME} — ${BRAND_TAGLINE}`,
    template: `%s · ${BRAND_NAME}`,
  },
  description: HOME_DESCRIPTION,
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://dineadeal.com",
  ),
  verification: {
    google: "ssmV4FvDAcNjtCIFDnboapf0iUEjVR361mdkZPOO2FM",
  },
  openGraph: {
    type: "website",
    siteName: BRAND_NAME,
    locale: "en_GB",
    title: `${BRAND_NAME} — ${BRAND_TAGLINE}`,
    description: HOME_DESCRIPTION,
    images: [{ url: "/logo-dineadeal.png", alt: `${BRAND_NAME} — ${BRAND_TAGLINE}` }],
  },
  twitter: {
    card: "summary",
    title: `${BRAND_NAME} — ${BRAND_TAGLINE}`,
    description: HOME_DESCRIPTION,
    images: ["/logo-dineadeal.png"],
  },
  icons: {
    // Prefer .ico for Chrome/Safari URL-bar; PNG fallbacks for tabs/PWA.
    icon: [
      { url: "/favicon.ico", type: "image/x-icon", sizes: "16x16 32x32 48x48" },
      { url: "/favicon.png", type: "image/png", sizes: "48x48" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    shortcut: [{ url: "/favicon.ico", type: "image/x-icon" }],
    apple: [{ url: "/apple-icon.png", sizes: "180x180", type: "image/png" }],
  },
  ...(adsenseClient
    ? { other: { "google-adsense-account": adsenseClient } }
    : {}),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const crawler = isAdCrawler(headers().get("user-agent"));

  return (
    <html lang="en-GB" className={`${oswald.variable} ${crimson.variable}`}>
      <body className="min-h-screen max-w-[100vw] overflow-x-clip font-sans">
        <CookieConsentProvider>
          <AdSenseScript />
          <VercelAnalytics />
          {/* Deal counter + public chrome — always visible, including merchant login */}
          <SiteHeader />
          <ConditionalSiteHeader>
            {crawler ? null : <NewsletterPopup />}
            <ScrollToTopButton />
          </ConditionalSiteHeader>
          {children}
        </CookieConsentProvider>
      </body>
    </html>
  );
}
