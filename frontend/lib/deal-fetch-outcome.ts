export type DealFetchPurpose = "metadata" | "page";

export type FailedDealFetch = {
  ok: false;
  error: string;
  status?: number;
};

/**
 * Only a real 404 means the deal is not indexable. A transient API failure
 * (timeout, pool exhaustion, 5xx, network) must not emit noindex on a live
 * deal: throw so Next.js serves an error and crawlers retry later.
 */
export function missingDealOrThrow(
  result: FailedDealFetch,
  purpose: DealFetchPurpose,
): void {
  if (result.status === 404) return;
  throw new Error(`fetchDeal failed for ${purpose}: ${result.error}`);
}
