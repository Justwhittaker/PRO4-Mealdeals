import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import { applyLegalPlaceholders } from "@/lib/legal-config";

/**
 * Renders legal prose with placeholder substitution and policy links.
 * Does not paraphrase — only wraps known phrases and replaces [TOKENS].
 */
export function LegalRichText({ text }: { text: string }) {
  const resolved = applyLegalPlaceholders(text);
  return <>{linkifyPolicies(resolved)}</>;
}

const POLICY_PATTERN =
  /(Privacy Notice|Cookie Policy)/g;

function linkifyPolicies(text: string): ReactNode[] {
  const parts = text.split(POLICY_PATTERN);
  return parts.map((part, index) => {
    if (part === "Privacy Notice") {
      return (
        <Link
          key={`pn-${index}`}
          href="/privacy"
          className="text-burgundy-600 underline-offset-2 hover:underline"
        >
          Privacy Notice
        </Link>
      );
    }
    if (part === "Cookie Policy") {
      return (
        <Link
          key={`cp-${index}`}
          href="/cookies"
          className="text-burgundy-600 underline-offset-2 hover:underline"
        >
          Cookie Policy
        </Link>
      );
    }
    return <Fragment key={`t-${index}`}>{part}</Fragment>;
  });
}
