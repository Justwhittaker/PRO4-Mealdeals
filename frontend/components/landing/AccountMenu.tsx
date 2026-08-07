"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { Mail, Megaphone, UserRound } from "lucide-react";

const MENU_ITEMS = [
  {
    href: "/dashboard",
    label: "Merchant Sign in",
    description: "Register & get the first month Free",
    icon: UserRound,
  },
  {
    href: "/dashboard",
    label: "Marketing portal",
    description: "Build an advert",
    icon: Megaphone,
  },
  {
    href: "/contact",
    label: "Contact us",
    description: "Email the Dine A Deal team",
    icon: Mail,
  },
] as const;

export function AccountMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="rounded-md p-2 text-charcoal-200 transition hover:bg-burgundy-50 hover:text-burgundy-600"
        aria-label="Merchant Sign in"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        <UserRound className="h-5 w-5 sm:h-6 sm:w-6" />
      </button>

      {open ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-md border border-charcoal-700 bg-white py-1 shadow-deal"
        >
          <p className="border-b border-charcoal-800 px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-charcoal-400">
            Account
          </p>
          {MENU_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                role="menuitem"
                className="flex items-start gap-3 px-3 py-2.5 text-left transition hover:bg-burgundy-50"
                onClick={() => setOpen(false)}
              >
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-burgundy-500" />
                <span>
                  <span className="block text-sm font-medium text-charcoal-50">
                    {item.label}
                  </span>
                  <span className="block text-xs text-charcoal-400">
                    {item.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
