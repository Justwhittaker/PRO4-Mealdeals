/**
 * Legal / Terms configuration for Dine A Deal.
 * Unknown values keep visible [PLACEHOLDER] text until set via env.
 */

import { BRAND_CONTACT_EMAIL, BRAND_NAME } from "@/lib/brand";
import { CONTACT_EMAIL } from "@/lib/contact";

export const TERMS_VERSION = "1.0";

/** Cookie set before Google OAuth from the merchant register form. */
export const TERMS_ACCEPT_COOKIE = "dad_terms_accept";

function envOrPlaceholder(
  envKey: string,
  placeholder: string,
): string {
  const value = process.env[envKey]?.trim();
  return value || placeholder;
}

function envOrFallback(
  envKey: string,
  fallback: string,
): string {
  const value = process.env[envKey]?.trim();
  return value || fallback;
}

/** Prefer public contact, then known CONTACT_EMAIL constant. */
const defaultSupportEmail =
  BRAND_CONTACT_EMAIL || CONTACT_EMAIL || "[SUPPORT EMAIL]";

/**
 * Company legal name as published on the Privacy Notice pages.
 * Override with NEXT_PUBLIC_LEGAL_COMPANY_NAME when the registered entity changes.
 */
const knownCompanyName = "CheddaCheeze";

export const legalConfig = {
  termsVersion: TERMS_VERSION,
  brandName: BRAND_NAME,
  effectiveDate: envOrPlaceholder(
    "NEXT_PUBLIC_TERMS_EFFECTIVE_DATE",
    "[EFFECTIVE DATE]",
  ),
  lastUpdated: envOrPlaceholder(
    "NEXT_PUBLIC_TERMS_LAST_UPDATED",
    "[LAST UPDATED DATE]",
  ),
  companyName: envOrFallback(
    "NEXT_PUBLIC_LEGAL_COMPANY_NAME",
    knownCompanyName,
  ),
  companyNumber: envOrPlaceholder(
    "NEXT_PUBLIC_COMPANY_NUMBER",
    "[COMPANY NUMBER]",
  ),
  registeredAddress: envOrPlaceholder(
    "NEXT_PUBLIC_REGISTERED_ADDRESS",
    "[REGISTERED ADDRESS]",
  ),
  postalAddress: envOrPlaceholder(
    "NEXT_PUBLIC_POSTAL_ADDRESS",
    "[POSTAL ADDRESS]",
  ),
  supportEmail: envOrFallback(
    "NEXT_PUBLIC_SUPPORT_EMAIL",
    defaultSupportEmail,
  ),
  complaintsEmail: envOrFallback(
    "NEXT_PUBLIC_COMPLAINTS_EMAIL",
    defaultSupportEmail,
  ),
  reportingEmail: envOrFallback(
    "NEXT_PUBLIC_REPORTING_EMAIL",
    defaultSupportEmail,
  ),
  billingEmail: envOrFallback(
    "NEXT_PUBLIC_BILLING_EMAIL",
    defaultSupportEmail,
  ),
  businessComplaintsEmail: envOrFallback(
    "NEXT_PUBLIC_BUSINESS_COMPLAINTS_EMAIL",
    defaultSupportEmail,
  ),
  phoneNumber: envOrPlaceholder(
    "NEXT_PUBLIC_LEGAL_PHONE",
    "[PHONE NUMBER]",
  ),
  /** May be an email or a path/URL description. */
  reportingEmailOrPage: envOrFallback(
    "NEXT_PUBLIC_REPORTING_CONTACT",
    defaultSupportEmail,
  ),
  appealsEmailOrPage: envOrFallback(
    "NEXT_PUBLIC_APPEALS_CONTACT",
    defaultSupportEmail,
  ),
} as const;

export type LegalConfig = typeof legalConfig;

/** Map square-bracket tokens in legal copy → resolved config values. */
export const LEGAL_PLACEHOLDERS: Record<string, string> = {
  "[EFFECTIVE DATE]": legalConfig.effectiveDate,
  "[LAST UPDATED DATE]": legalConfig.lastUpdated,
  "[LEGAL COMPANY NAME]": legalConfig.companyName,
  "[COMPANY NUMBER]": legalConfig.companyNumber,
  "[REGISTERED ADDRESS]": legalConfig.registeredAddress,
  "[SUPPORT EMAIL]": legalConfig.supportEmail,
  "[COMPLAINTS EMAIL]": legalConfig.complaintsEmail,
  "[REPORTING EMAIL]": legalConfig.reportingEmail,
  "[PHONE NUMBER]": legalConfig.phoneNumber,
  "[POSTAL ADDRESS]": legalConfig.postalAddress,
  "[BILLING EMAIL]": legalConfig.billingEmail,
  "[REPORTING EMAIL OR REPORTING PAGE]": legalConfig.reportingEmailOrPage,
  "[APPEALS EMAIL OR APPEALS PAGE]": legalConfig.appealsEmailOrPage,
  "[BUSINESS COMPLAINTS EMAIL]": legalConfig.businessComplaintsEmail,
};

export function applyLegalPlaceholders(text: string): string {
  let out = text;
  for (const [token, value] of Object.entries(LEGAL_PLACEHOLDERS)) {
    out = out.split(token).join(value);
  }
  return out;
}
