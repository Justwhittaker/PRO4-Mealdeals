import Link from "next/link";

interface FeedPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  /** Current path without query, e.g. /us/new-york */
  pathname: string;
  /** Existing search params to preserve (currency, sort, …). */
  searchParams?: Record<string, string | undefined>;
}

function buildHref(
  pathname: string,
  searchParams: Record<string, string | undefined> | undefined,
  page: number,
): string {
  const params = new URLSearchParams();
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (key === "page") continue;
      if (value != null && value !== "") params.set(key, value);
    }
  }
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

/**
 * Prev / next for area deal listings. Uses links so pages stay crawlable.
 */
export function FeedPagination({
  page,
  pageSize,
  total,
  pathname,
  searchParams,
}: FeedPaginationProps) {
  if (total <= pageSize) return null;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(page, 1), totalPages);
  const from = (current - 1) * pageSize + 1;
  const to = Math.min(current * pageSize, total);
  const prev = current > 1 ? current - 1 : null;
  const next = current < totalPages ? current + 1 : null;

  const linkClass =
    "inline-flex min-w-[6.5rem] items-center justify-center border border-charcoal-700 bg-white px-3 py-2 text-sm text-charcoal-200 transition hover:border-burgundy-300 hover:text-burgundy-600";
  const disabledClass =
    "inline-flex min-w-[6.5rem] items-center justify-center border border-charcoal-700/50 bg-charcoal-900/5 px-3 py-2 text-sm text-charcoal-400";

  return (
    <nav
      className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-between"
      aria-label="Deal list pages"
    >
      <p className="text-sm text-charcoal-400">
        Showing {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-2">
        {prev != null ? (
          <Link
            href={buildHref(pathname, searchParams, prev)}
            className={linkClass}
            rel="prev"
          >
            Previous
          </Link>
        ) : (
          <span className={disabledClass} aria-disabled="true">
            Previous
          </span>
        )}
        <span className="px-2 text-sm text-charcoal-300">
          Page {current} of {totalPages}
        </span>
        {next != null ? (
          <Link
            href={buildHref(pathname, searchParams, next)}
            className={linkClass}
            rel="next"
          >
            Next
          </Link>
        ) : (
          <span className={disabledClass} aria-disabled="true">
            Next
          </span>
        )}
      </div>
    </nav>
  );
}
