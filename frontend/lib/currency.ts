/** ISO currency helpers keyed by MealDeals country slugs. */

export type CurrencyCode = string;

export interface CurrencyMeta {
  code: CurrencyCode;
  symbol: string;
  label: string;
}

export const CURRENCIES: Record<string, CurrencyMeta> = {
  AED: { code: "AED", symbol: 'د.إ', label: 'UAE Dirham' },
  ARS: { code: "ARS", symbol: '$', label: 'Argentine Peso' },
  AUD: { code: "AUD", symbol: 'A$', label: 'Australian Dollar' },
  BBD: { code: "BBD", symbol: 'Bds$', label: 'Barbadian Dollar' },
  BRL: { code: "BRL", symbol: 'R$', label: 'Brazilian Real' },
  BSD: { code: "BSD", symbol: 'B$', label: 'Bahamian Dollar' },
  BWP: { code: "BWP", symbol: 'P', label: 'Botswana Pula' },
  BZD: { code: "BZD", symbol: 'BZ$', label: 'Belize Dollar' },
  CAD: { code: "CAD", symbol: 'C$', label: 'Canadian Dollar' },
  CHF: { code: "CHF", symbol: 'CHF', label: 'Swiss Franc' },
  CLP: { code: "CLP", symbol: '$', label: 'Chilean Peso' },
  CNY: { code: "CNY", symbol: '¥', label: 'Chinese Yuan' },
  COP: { code: "COP", symbol: '$', label: 'Colombian Peso' },
  CZK: { code: "CZK", symbol: 'Kč', label: 'Czech Koruna' },
  DKK: { code: "DKK", symbol: 'kr', label: 'Danish Krone' },
  EGP: { code: "EGP", symbol: 'E£', label: 'Egyptian Pound' },
  EUR: { code: "EUR", symbol: '€', label: 'Euro' },
  FJD: { code: "FJD", symbol: 'FJ$', label: 'Fijian Dollar' },
  GBP: { code: "GBP", symbol: '£', label: 'British Pound' },
  GHS: { code: "GHS", symbol: 'GH₵', label: 'Ghanaian Cedi' },
  GMD: { code: "GMD", symbol: 'D', label: 'Gambian Dalasi' },
  GYD: { code: "GYD", symbol: 'G$', label: 'Guyanese Dollar' },
  IDR: { code: "IDR", symbol: 'Rp', label: 'Indonesian Rupiah' },
  ILS: { code: "ILS", symbol: '₪', label: 'Israeli Shekel' },
  INR: { code: "INR", symbol: '₹', label: 'Indian Rupee' },
  ISK: { code: "ISK", symbol: 'kr', label: 'Icelandic Krona' },
  JMD: { code: "JMD", symbol: 'J$', label: 'Jamaican Dollar' },
  JOD: { code: "JOD", symbol: 'د.ا', label: 'Jordanian Dinar' },
  JPY: { code: "JPY", symbol: '¥', label: 'Japanese Yen' },
  KES: { code: "KES", symbol: 'KSh', label: 'Kenyan Shilling' },
  KRW: { code: "KRW", symbol: '₩', label: 'South Korean Won' },
  LRD: { code: "LRD", symbol: 'L$', label: 'Liberian Dollar' },
  LSL: { code: "LSL", symbol: 'L', label: 'Lesotho Loti' },
  MAD: { code: "MAD", symbol: 'د.م.', label: 'Moroccan Dirham' },
  MWK: { code: "MWK", symbol: 'MK', label: 'Malawian Kwacha' },
  MXN: { code: "MXN", symbol: 'MX$', label: 'Mexican Peso' },
  MYR: { code: "MYR", symbol: 'RM', label: 'Malaysian Ringgit' },
  NAD: { code: "NAD", symbol: 'N$', label: 'Namibian Dollar' },
  NGN: { code: "NGN", symbol: '₦', label: 'Nigerian Naira' },
  NOK: { code: "NOK", symbol: 'kr', label: 'Norwegian Krone' },
  NZD: { code: "NZD", symbol: 'NZ$', label: 'New Zealand Dollar' },
  PGK: { code: "PGK", symbol: 'K', label: 'Papua New Guinean Kina' },
  PHP: { code: "PHP", symbol: '₱', label: 'Philippine Peso' },
  PKR: { code: "PKR", symbol: '₨', label: 'Pakistani Rupee' },
  PLN: { code: "PLN", symbol: 'zł', label: 'Polish Zloty' },
  QAR: { code: "QAR", symbol: 'ر.ق', label: 'Qatari Riyal' },
  RWF: { code: "RWF", symbol: 'FRw', label: 'Rwandan Franc' },
  SBD: { code: "SBD", symbol: 'SI$', label: 'Solomon Islands Dollar' },
  SEK: { code: "SEK", symbol: 'kr', label: 'Swedish Krona' },
  SGD: { code: "SGD", symbol: 'S$', label: 'Singapore Dollar' },
  SLE: { code: "SLE", symbol: 'Le', label: 'Sierra Leonean Leone' },
  SSP: { code: "SSP", symbol: 'SSP', label: 'South Sudanese Pound' },
  SZL: { code: "SZL", symbol: 'E', label: 'Swazi Lilangeni' },
  THB: { code: "THB", symbol: '฿', label: 'Thai Baht' },
  TND: { code: "TND", symbol: 'د.ت', label: 'Tunisian Dinar' },
  TOP: { code: "TOP", symbol: 'T$', label: 'Tongan Paʻanga' },
  TRY: { code: "TRY", symbol: '₺', label: 'Turkish Lira' },
  TTD: { code: "TTD", symbol: 'TT$', label: 'Trinidad Dollar' },
  UGX: { code: "UGX", symbol: 'USh', label: 'Ugandan Shilling' },
  USD: { code: "USD", symbol: '$', label: 'US Dollar' },
  VND: { code: "VND", symbol: '₫', label: 'Vietnamese Dong' },
  VUV: { code: "VUV", symbol: 'VT', label: 'Vanuatu Vatu' },
  WST: { code: "WST", symbol: 'T', label: 'Samoan Tala' },
  XAF: { code: "XAF", symbol: 'FCFA', label: 'Central African CFA Franc' },
  XCD: { code: "XCD", symbol: 'EC$', label: 'East Caribbean Dollar' },
  ZAR: { code: "ZAR", symbol: 'R', label: 'South African Rand' },
  ZMW: { code: "ZMW", symbol: 'ZK', label: 'Zambian Kwacha' },
};

/** Country slug (lowercase ISO / uk) → local display currency. */
export const COUNTRY_CURRENCY: Record<string, CurrencyCode> = {
  ae: "AED",
  ag: "XCD",
  ar: "ARS",
  at: "EUR",
  au: "AUD",
  bb: "BBD",
  be: "EUR",
  br: "BRL",
  bs: "BSD",
  bw: "BWP",
  bz: "BZD",
  ca: "CAD",
  ch: "CHF",
  cl: "CLP",
  cm: "XAF",
  cn: "CNY",
  co: "COP",
  cz: "CZK",
  de: "EUR",
  dk: "DKK",
  eg: "EGP",
  es: "EUR",
  fi: "EUR",
  fj: "FJD",
  fm: "USD",
  fr: "EUR",
  gb: "GBP",
  gd: "XCD",
  gh: "GHS",
  gm: "GMD",
  gr: "EUR",
  gy: "GYD",
  hr: "EUR",
  id: "IDR",
  ie: "EUR",
  il: "ILS",
  in: "INR",
  is: "ISK",
  it: "EUR",
  jm: "JMD",
  jo: "JOD",
  jp: "JPY",
  ke: "KES",
  ki: "AUD",
  kn: "XCD",
  kr: "KRW",
  lr: "LRD",
  ls: "LSL",
  ma: "MAD",
  mh: "USD",
  mt: "EUR",
  mw: "MWK",
  mx: "MXN",
  my: "MYR",
  na: "NAD",
  ng: "NGN",
  nl: "EUR",
  no: "NOK",
  nr: "AUD",
  nz: "NZD",
  pg: "PGK",
  ph: "PHP",
  pk: "PKR",
  pl: "PLN",
  pt: "EUR",
  pw: "USD",
  qa: "QAR",
  rw: "RWF",
  sb: "SBD",
  se: "SEK",
  sg: "SGD",
  si: "EUR",
  sk: "EUR",
  sl: "SLE",
  ss: "SSP",
  sz: "SZL",
  th: "THB",
  tn: "TND",
  to: "TOP",
  tr: "TRY",
  tt: "TTD",
  tv: "AUD",
  ug: "UGX",
  us: "USD",
  vc: "XCD",
  vn: "VND",
  vu: "VUV",
  ws: "WST",
  za: "ZAR",
  zm: "ZMW",
  zw: "USD",
  uk: "GBP",
};

/** Featured monthly prices by currency */
export const FEATURED_PRICES: Partial<Record<string, number>> = {
  USD: 39,
  GBP: 29,
  EUR: 35,
  AUD: 55,
};

/** Enterprise yearly prices */
export const ENTERPRISE_PRICES: Partial<Record<string, number>> = {
  USD: 399,
  GBP: 299,
};

export function formatMoney(
  amount: number,
  currency: CurrencyCode = "USD",
  locale = "en-US",
): string {
  const code = (currency || "USD").toUpperCase();
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: code,
      maximumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    }).format(amount);
  } catch {
    const meta = CURRENCIES[code];
    const symbol = meta?.symbol ?? code;
    return `${symbol}${amount.toFixed(Number.isInteger(amount) ? 0 : 2)}`;
  }
}

export function currencyForCountry(countryCode: string): CurrencyCode {
  const key = countryCode.trim().toLowerCase();
  return COUNTRY_CURRENCY[key] ?? "USD";
}

export function isCurrencyCode(value: string | undefined | null): value is CurrencyCode {
  if (!value) return false;
  return value.toUpperCase() in CURRENCIES;
}

/** Currencies shown in the selector: local first, then major, then the rest. */
export function currenciesForSelector(countryCode?: string): CurrencyCode[] {
  const local = countryCode ? currencyForCountry(countryCode) : null;
  const major = ["USD", "GBP", "EUR", "AUD", "CAD", "NZD", "JPY", "INR", "ZAR", "SGD"];
  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const code of [local, ...major, ...Object.keys(CURRENCIES)].filter(Boolean) as string[]) {
    const upper = code.toUpperCase();
    if (seen.has(upper) || !(upper in CURRENCIES)) continue;
    seen.add(upper);
    ordered.push(upper);
  }
  return ordered;
}
