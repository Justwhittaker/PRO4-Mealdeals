"use client";

import { useEffect, useState } from "react";
import { DEAL_IMAGE_FALLBACK, cleanMediaUrl } from "@/lib/deal-media";

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

/**
 * Deal hero photo with optional circular company logo at bottom-left.
 * Logo only when merchant.logo_url is present and loads — never a placeholder.
 * When the deal photo is missing/broken, fall back to a local hero so cards
 * never show an empty charcoal slab.
 */
export function DealHeroMedia({
  imageUrl,
  logoUrl,
  restaurantName,
  aspectClassName = "aspect-[16/9]",
  className = "",
  hoverZoom = false,
}: DealHeroMediaProps) {
  const resolvedImage = cleanMediaUrl(imageUrl);
  const resolvedLogo = cleanMediaUrl(logoUrl);
  const [imageFailed, setImageFailed] = useState(false);
  const [fallbackFailed, setFallbackFailed] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
    setFallbackFailed(false);
  }, [resolvedImage]);

  useEffect(() => {
    setLogoFailed(false);
  }, [resolvedLogo]);

  const primarySrc =
    resolvedImage && !imageFailed ? resolvedImage : null;
  const showFallback = !primarySrc && !fallbackFailed;
  const showLogo = Boolean(resolvedLogo) && !logoFailed;

  const imgClass = hoverZoom
    ? "h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
    : "h-full w-full object-cover";

  return (
    <div
      className={`relative overflow-hidden bg-charcoal-900 ${aspectClassName} ${className}`}
    >
      {primarySrc ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={primarySrc}
          src={primarySrc}
          alt=""
          className={imgClass}
          referrerPolicy="no-referrer"
          loading="lazy"
          decoding="async"
          onError={() => setImageFailed(true)}
        />
      ) : showFallback ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={DEAL_IMAGE_FALLBACK}
          src={DEAL_IMAGE_FALLBACK}
          alt=""
          className={imgClass}
          loading="lazy"
          decoding="async"
          onError={() => setFallbackFailed(true)}
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
