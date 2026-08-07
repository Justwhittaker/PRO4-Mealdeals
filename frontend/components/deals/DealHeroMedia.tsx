"use client";

import { useEffect, useState } from "react";

interface DealHeroMediaProps {
  imageUrl?: string | null;
  logoUrl?: string | null;
  restaurantName?: string;
  /** Aspect ratio utility class, e.g. aspect-[16/10] */
  aspectClassName?: string;
  /** Extra classes on the outer frame */
  className?: string;
  /** Scale image slightly on group hover (cards) */
  hoverZoom?: boolean;
}

/** Real http(s) media URL — excludes placeholders / tracking pixels. */
function usableContentUrl(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^https?:\/\//i.test(trimmed)) return null;
  const lower = trimmed.toLowerCase();
  if (
    /(placeholder|sprite|pixel|1x1|tracking|spacer|blank\.gif)/i.test(lower)
  ) {
    return null;
  }
  return trimmed;
}

/**
 * Deal hero photo with optional circular company logo at bottom-left.
 * Logo only when merchant.logo_url is present and loads — never a placeholder.
 */
export function DealHeroMedia({
  imageUrl,
  logoUrl,
  restaurantName,
  aspectClassName = "aspect-[16/9]",
  className = "",
  hoverZoom = false,
}: DealHeroMediaProps) {
  const resolvedImage = usableContentUrl(imageUrl);
  const resolvedLogo = usableContentUrl(logoUrl);
  const [imageFailed, setImageFailed] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [resolvedImage]);

  useEffect(() => {
    setLogoFailed(false);
  }, [resolvedLogo]);

  const showImage = Boolean(resolvedImage) && !imageFailed;
  const showLogo = Boolean(resolvedLogo) && !logoFailed;

  const imgClass = hoverZoom
    ? "h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
    : "h-full w-full object-cover";

  return (
    <div
      className={`relative overflow-hidden bg-charcoal-900 ${aspectClassName} ${className}`}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={resolvedImage!}
          src={resolvedImage!}
          alt=""
          className={imgClass}
          referrerPolicy="no-referrer"
          loading="lazy"
          decoding="async"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <div
          className="h-full w-full bg-gradient-to-br from-charcoal-900 via-charcoal-800 to-burgundy-900/40"
          aria-hidden
        />
      )}
      {showLogo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={resolvedLogo!}
          src={resolvedLogo!}
          alt={restaurantName ? `${restaurantName} logo` : "Company logo"}
          className="absolute bottom-3 left-3 z-[1] h-10 w-10 rounded-full border-2 border-white/90 bg-white object-contain shadow-md sm:h-12 sm:w-12"
          referrerPolicy="no-referrer"
          loading="lazy"
          decoding="async"
          onError={() => setLogoFailed(true)}
        />
      ) : null}
    </div>
  );
}
