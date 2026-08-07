"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CURRENCIES,
  currenciesForSelector,
  type CurrencyCode,
} from "@/lib/currency";

interface CurrencySelectorProps {
  value: CurrencyCode;
  /** When set, local currency is listed first and used as the default hint. */
  country?: string;
}

export function CurrencySelector({ value, country }: CurrencySelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const options = currenciesForSelector(country);
  const current = value.toUpperCase();

  function onChange(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("currency", next.toUpperCase());
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="w-[150px]">
      <Select value={current} onValueChange={onChange}>
        <SelectTrigger aria-label="Currency">
          <SelectValue placeholder="Currency" />
        </SelectTrigger>
        <SelectContent>
          {options.map((code) => {
            const meta = CURRENCIES[code];
            return (
              <SelectItem key={code} value={code}>
                {meta?.symbol ?? code} {code}
                {country && code === options[0] ? " · local" : ""}
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </div>
  );
}
