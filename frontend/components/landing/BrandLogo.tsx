import Image from "next/image";
import Link from "next/link";
import {
  BRAND_LOGO_SRC,
  BRAND_NAME,
  BRAND_WORDMARK_SRC,
} from "@/lib/brand";

type BrandLogoSize = "sm" | "md" | "lg";

const SIZE: Record<
  BrandLogoSize,
  { logo: string; word: string; logoPx: number; wordSizes: string }
> = {
  sm: {
    logo: "h-12 w-12",
    word: "h-12 w-[11.25rem]",
    logoPx: 48,
    wordSizes: "180px",
  },
  md: {
    logo: "h-10 w-10 sm:h-16 sm:w-16 md:h-20 md:w-20",
    word:
      "h-10 w-[8.5rem] max-w-[min(8.5rem,36vw)] sm:h-[3.75rem] sm:w-[15rem] sm:max-w-none md:h-[4.5rem] md:w-[19.5rem]",
    logoPx: 80,
    wordSizes: "(max-width: 640px) 136px, 312px",
  },
  lg: {
    logo: "h-16 w-16 sm:h-24 sm:w-24",
    word:
      "h-14 w-[min(12rem,calc(100vw-7rem))] sm:h-[5.25rem] sm:w-96 sm:max-w-none",
    logoPx: 96,
    wordSizes: "(max-width: 640px) 192px, 384px",
  },
};

interface BrandLogoProps {
  size?: BrandLogoSize;
  href?: string | null;
  priority?: boolean;
  className?: string;
}

/** Logo + home wordmark side by side. */
export function BrandLogo({
  size = "md",
  href = "/",
  priority = false,
  className = "",
}: BrandLogoProps) {
  const s = SIZE[size];
  const content = (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className={`relative ${s.logo}`}>
        <Image
          src={BRAND_LOGO_SRC}
          alt=""
          fill
          className="object-contain"
          sizes={`${s.logoPx}px`}
          priority={priority}
        />
      </span>
      <span className={`relative ${s.word}`}>
        <Image
          src={BRAND_WORDMARK_SRC}
          alt={BRAND_NAME}
          fill
          className="object-contain object-left"
          sizes={s.wordSizes}
          priority={priority}
        />
      </span>
    </span>
  );

  if (!href) return content;

  return (
    <Link
      href={href}
      aria-label={`${BRAND_NAME} home`}
      className="inline-flex max-w-full"
    >
      {content}
    </Link>
  );
}
