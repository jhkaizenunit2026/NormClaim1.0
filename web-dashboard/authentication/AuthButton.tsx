"use client";

import { useAuthDialog } from "@/hooks/useAuthDialog";
import type { AuthMode } from "@/types/auth";
import type { ReactNode, ButtonHTMLAttributes } from "react";

interface AuthButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** If provided, wrap a protected action — opens dialog if not logged in */
  protectedAction?: () => void;
  /** Which dialog mode to open when not authenticated */
  mode?: AuthMode;
  /** Render as a different element shape */
  variant?: "default" | "ghost" | "outline";
  children: ReactNode;
}

/**
 * AuthButton
 * Drop-in replacement for any <button> that needs auth.
 *
 * Usage A — open dialog directly:
 *   <AuthButton mode="signup">Sign up</AuthButton>
 *
 * Usage B — protect an action:
 *   <AuthButton protectedAction={() => submitClaim()}>
 *     Submit pre-auth
 *   </AuthButton>
 */
export function AuthButton({
  protectedAction,
  mode = "login",
  variant = "default",
  children,
  className = "",
  ...rest
}: AuthButtonProps) {
  const { requireAuth, openLogin, openSignup } = useAuthDialog();

  const handleClick = () => {
    if (protectedAction) {
      requireAuth(protectedAction, mode);
    } else if (mode === "signup") {
      openSignup();
    } else {
      openLogin();
    }
  };

  const base =
    "inline-flex items-center justify-center gap-2 font-medium text-sm rounded-lg px-4 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/60";

  const variants = {
    default: "bg-orange-500 hover:bg-orange-600 text-white",
    ghost: "text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800",
    outline:
      "border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800",
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`${base} ${variants[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
