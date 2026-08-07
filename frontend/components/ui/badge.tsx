import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-burgundy-50 text-burgundy-700",
        secondary: "border-transparent bg-charcoal-800 text-charcoal-200",
        outline: "border-charcoal-600 text-charcoal-200",
        verified: "border-burgundy-300 bg-burgundy-50 text-burgundy-700",
        external: "border-charcoal-600 bg-charcoal-900 text-charcoal-300",
        featured: "border-amber-400 bg-amber-50 text-amber-800",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
