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
  currenciesAlphabetical,
  type CurrencyCode,
} from "@/lib/currency";

interface CurrencySelectorProps {
  value: CurrencyCode;
  /** When set, local currency is listed first and used as the default hint. */
  country?: string;
}

export function CurrencySelector({ value }: CurrencySelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const options = currenciesAlphabetical();
  const current = value.toUpperCase();

  function onChange(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("currency", next.toUpperCase());
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="w-[170px]">
      <Select value={current} onValueChange={onChange}>
        <SelectTrigger aria-label="Currency">
          <SelectValue placeholder="Currency" />
        </SelectTrigger>
        <SelectContent className="max-h-72">
          {options.map(({ code, label }) => (
            <SelectItem key={code} value={code}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
