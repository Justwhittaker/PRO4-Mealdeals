interface NewsletterAuthIntroProps {
  titleId?: string;
  as?: "h1" | "h2";
  className?: string;
}

/**
 * Shared eyebrow / headline / body for newsletter popup and portal.
 * Keep copy here so signup surfaces cannot drift apart.
 */
export function NewsletterAuthIntro({
  titleId,
  as = "h1",
  className,
}: NewsletterAuthIntroProps) {
  const Title = as;

  return (
    <div className={className}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-burgundy-500">
        Customer newsletter
      </p>
      <Title
        id={titleId}
        className="mt-2 font-display text-3xl leading-tight text-charcoal-50 sm:text-4xl"
      >
        Weekly Hot Deals newsletter
      </Title>
      <p className="mt-3 text-sm leading-relaxed text-charcoal-300">
        New readers sign up with first name, surname, email, and location.
        Already on the list? Sign in with your email to restore deals on this
        device. Unsubscribe pauses emails — your record stays so you can come
        back anytime.
      </p>
    </div>
  );
}
