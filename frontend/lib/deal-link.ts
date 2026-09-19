export type DealLinkKind = "specific" | "listing" | "homepage";

/** Fallback CTA when API does not send cta_label (older backend). */
export function dealCtaLabel(
  linkKind: DealLinkKind | null | undefined,
  merchantName: string,
): string {
  const name = merchantName.trim() || "this venue";
  switch (linkKind) {
    case "specific":
      return "Claim this deal";
    case "listing":
      return `View offers on ${name}`;
    case "homepage":
    default:
      return `Visit ${name} website`;
  }
}

/** Short hint under the CTA so users know what to expect. */
export function dealLinkHint(
  linkKind: DealLinkKind | null | undefined,
): string | null {
  switch (linkKind) {
    case "listing":
      return "Opens the venue's offers or promotions page.";
    case "homepage":
      return "Opens the venue website — browse their current offers there.";
    default:
      return null;
  }
}
