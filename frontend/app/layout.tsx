import type { Metadata } from "next";
import { Crimson_Text, Oswald } from "next/font/google";
import { AdSenseScript } from "@/components/ads/AdSenseScript";
import { ConditionalSiteHeader } from "@/components/landing/ConditionalSiteHeader";
import { SiteHeader } from "@/components/landing/SiteHeader";
import { BRAND_NAME, BRAND_TAGLINE } from "@/lib/brand";
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

export const metadata: Metadata = {
  title: {
    default: `${BRAND_NAME} — ${BRAND_TAGLINE}`,
    template: `%s · ${BRAND_NAME}`,
  },
  description:
    "Find dining deals near you across cities worldwide. Restaurants advertise on a flat-rate platform — no voucher cut.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://dineadeal.com",
  ),
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
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${oswald.variable} ${crimson.variable}`}>
      <body className="min-h-screen font-sans">
        <AdSenseScript />
        <ConditionalSiteHeader>
          <SiteHeader />
        </ConditionalSiteHeader>
        {children}
      </body>
    </html>
  );
}
