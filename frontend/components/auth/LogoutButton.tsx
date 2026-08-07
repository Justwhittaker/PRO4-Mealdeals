"use client";

import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LogoutButtonProps {
  variant?: "default" | "secondary" | "outline" | "ghost" | "link";
  className?: string;
  label?: string;
}

export function LogoutButton({
  variant = "outline",
  className,
  label = "Log out",
}: LogoutButtonProps) {
  return (
    <Button
      type="button"
      variant={variant}
      className={className}
      onClick={() => signOut({ callbackUrl: "/" })}
    >
      <LogOut className="h-4 w-4" />
      {label}
    </Button>
  );
}
