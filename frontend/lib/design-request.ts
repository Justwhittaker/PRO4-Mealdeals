/** Merchant-facing short tag from a design request UUID (last 6 hex chars). */
export function designRequestShortRef(id: string): string {
  const hex = id.replace(/-/g, "").toLowerCase();
  const short = hex.slice(-6) || hex;
  return `DESIGN:${short}`;
}
