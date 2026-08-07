interface AdPlaceholderProps {
  label?: string;
  hint?: string;
  minHeight?: number;
  className?: string;
}

/** Reserved CLS-safe slot shown until AdSense can serve on a public URL. */
export function AdPlaceholder({
  label = "Sponsored",
  hint = "Ads unlock on the live site URL",
  minHeight = 120,
  className = "",
}: AdPlaceholderProps) {
  return (
    <div
      className={`flex w-full flex-col items-center justify-center gap-1 px-4 py-6 text-center ${className}`}
      style={{ minHeight }}
    >
      <p className="text-xs uppercase tracking-widest text-charcoal-500">
        {label}
      </p>
      <p className="text-[11px] text-charcoal-600">{hint}</p>
    </div>
  );
}
