import type { CurrencyCode } from "@/lib/currency";
import { PRIORITY_EUR } from "@/lib/stripe";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Stub FX aligned with backend celery rates (units per 1 USD). */
const FALLBACK_USD_RATES: Partial<Record<string, number>> = {
  USD: 1,
  EUR: 0.92,
  GBP: 0.79,
  CAD: 1.36,
  AUD: 1.52,
  NZD: 1.65,
  SGD: 1.34,
  ZAR: 18.5,
  JPY: 150,
  INR: 83,
  AED: 3.6725,
};

function convertLocal(
  amount: number,
  from: CurrencyCode,
  to: CurrencyCode,
): number {
  if (from === to) return amount;
  const fromRate = FALLBACK_USD_RATES[from.toUpperCase()] ?? 1;
  const toRate = FALLBACK_USD_RATES[to.toUpperCase()] ?? 1;
  const usd = amount / fromRate;
  return Math.round(usd * toRate * 100) / 100;
}

export async function convertFromEur(
  amountEur: number,
  to: CurrencyCode,
): Promise<number> {
  if (to === "EUR") return amountEur;
  try {
    const qs = new URLSearchParams({
      amount: String(amountEur),
      from_currency: "EUR",
      to_currency: to,
    });
    const res = await fetch(
      `${API_URL.replace(/\/$/, "")}/api/v1/currency/convert?${qs}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const data = (await res.json()) as { converted: number };
      if (Number.isFinite(data.converted)) {
        return Math.round(data.converted * 100) / 100;
      }
    }
  } catch {
    // fall through
  }
  return convertLocal(amountEur, "EUR", to);
}

export async function resolvePriorityAmounts(currency: CurrencyCode): Promise<{
  currency: CurrencyCode;
  monthly: number;
  promoThreeMonths: number;
  monthlyCents: number;
  promoCents: number;
}> {
  const monthly = await convertFromEur(PRIORITY_EUR.monthly, currency);
  const promoThreeMonths = await convertFromEur(
    PRIORITY_EUR.promoThreeMonths,
    currency,
  );
  return {
    currency,
    monthly,
    promoThreeMonths,
    monthlyCents: Math.round(monthly * 100),
    promoCents: Math.round(promoThreeMonths * 100),
  };
}
