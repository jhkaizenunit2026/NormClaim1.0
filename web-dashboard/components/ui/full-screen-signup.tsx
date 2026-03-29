"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Briefcase,
  Building2,
  Landmark,
  Loader2,
  LogIn,
  Sun,
  User,
  UserPlus,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AuthMode, RoleCode } from "@/auth/types";
import {
  DEFAULT_DISPLAY_NAMES,
  ROLE_LABELS,
  ROLES_LIST,
} from "@/auth/types";
import {
  validateEmail,
  validateName,
  validatePassword,
} from "@/auth/utils/validation";
import { signInWithRole, signUpAccount } from "@/auth/services/auth.service";

const Sunburst = Sun;

export interface FullScreenSignupProps {
  /** Full-page layout for previews (no modal shell). */
  embedded?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  initialMode?: AuthMode;
  initialRole?: RoleCode | null;
}

const roleIcon = {
  HOSPITAL: Building2,
  TPA: Briefcase,
  FINANCE: Landmark,
} as const;



const LEFT_BG =
  "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?q=80&w=1200&auto=format&fit=crop";

export function FullScreenSignup({
  embedded = false,
  open = true,
  onOpenChange,
  initialMode = "signin",
  initialRole = null,
}: FullScreenSignupProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [role, setRole] = useState<RoleCode>(initialRole ?? "HOSPITAL");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [name, setName] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const resetFields = useCallback(() => {
    setEmail("");
    setPassword("");
    setConfirm("");
    setName("");
    setFieldErrors({});
    setFormError(null);
  }, []);

  const visible = embedded || open;

  useEffect(() => {
    if (!visible) return;
    setMode(initialMode);
    setRole(initialRole ?? "HOSPITAL");
    resetFields();
    if (initialRole) setName(DEFAULT_DISPLAY_NAMES[initialRole]);
  }, [visible, initialMode, initialRole, resetFields]);

  useEffect(() => {
    if (!visible || embedded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !pending) onOpenChange?.(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, embedded, onOpenChange, pending]);

  useEffect(() => {
    if (visible && !embedded) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [visible, embedded]);

  if (!visible) return null;

  const runValidation = (): boolean => {
    const next: Record<string, string> = {};
    const eErr = validateEmail(email);
    if (eErr) next.email = eErr;

    if (mode === "signin") {
      if (!password) next.password = "Password is required.";
    } else {
      const pErr = validatePassword(password, 8);
      if (pErr) next.password = pErr;
    }

    if (mode === "signup") {
      const nErr = validateName(name);
      if (nErr) next.name = nErr;
      if (password !== confirm) next.confirm = "Passwords do not match.";
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setFormError(null);
    if (!runValidation()) return;
    setPending(true);
    try {
      if (mode === "signin") {
        await signInWithRole(email.trim(), password, role);
      } else {
        await signUpAccount(email.trim(), password, name.trim(), role);
      }
      resetFields();
      onOpenChange?.(false);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Something went wrong."
      );
    } finally {
      setPending(false);
    }
  };

  const close = () => !pending && onOpenChange?.(false);

  const card = (
    <div
      className={cn(
        "w-full relative max-w-5xl overflow-hidden flex flex-col md:flex-row shadow-2xl rounded-3xl",
        !embedded && "max-h-[min(100vh-2rem,900px)]"
      )}
      role={embedded ? undefined : "document"}
    >
      {/* Decorative layers (reference layout) */}
      <div
        className="pointer-events-none absolute inset-0 z-[1] bg-cover bg-center opacity-40 md:opacity-50"
        style={{ backgroundImage: `url(${LEFT_BG})` }}
      />
      <div className="pointer-events-none absolute inset-0 z-[2] bg-gradient-to-t from-transparent to-black" />
  <div className="pointer-events-none w-60 h-60 nc-bg-accent absolute z-[1] rounded-full -bottom-20 -left-16 blur-sm opacity-90" />
      <div className="pointer-events-none w-32 h-20 bg-white absolute z-[1] rounded-full bottom-2 left-24 opacity-25 blur-md" />
      <div className="pointer-events-none w-28 h-16 bg-white absolute z-[1] rounded-full bottom-8 left-48 opacity-20 blur-md" />

      {/* Left column */}
      <div className="bg-black text-white p-8 md:p-12 md:w-1/2 relative rounded-bl-3xl md:rounded-bl-3xl overflow-hidden flex flex-col justify-end min-h-[280px] md:min-h-[32rem]">
        <div className="relative z-10">
          <p className="nc-accent text-sm font-medium mb-3 tracking-wide uppercase">
            NormClaim
          </p>
          <h1
            id="nc-auth-title"
            className="text-2xl md:text-3xl font-medium leading-tight tracking-tight"
          >
            Clinical claims partner for hospitals, TPAs, and finance teams.
          </h1>
          <p className="mt-4 text-sm text-white/70 max-w-md">
            Pre-authorization through settlement — one secure workflow for
            Indian healthcare claims.
          </p>
        </div>
      </div>

      {/* Right column — form */}
      <div className="p-8 md:p-12 md:w-1/2 flex flex-col bg-black text-white relative z-[20] overflow-y-auto">
        {!embedded && (
          <button
            type="button"
            onClick={close}
            className="absolute right-4 top-4 rounded-lg p-2 text-neutral-400 transition hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        )}

        <div className="flex flex-col items-start mb-6 md:mb-8">
          <div className="nc-accent mb-4">
            <Sunburst className="h-10 w-10" strokeWidth={1.5} />
          </div>
          <h2 className="text-3xl font-medium mb-2 tracking-tight text-white">
            {mode === "signup" ? "Get started" : "Welcome back"}
          </h2>
          <p className="text-left text-neutral-400 text-sm md:text-base">
            {mode === "signup"
              ? "Create your NormClaim account — choose your role and sign up."
              : "Sign in to continue to your dashboard."}
          </p>
        </div>

        <div className="flex gap-2 mb-6 w-full">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setFormError(null);
            }}
              className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition border",
              mode === "signin"
                ? "nc-border-accent nc-bg-accent-20 nc-accent"
                : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-500"
            )}
          >
            <LogIn className="h-4 w-4" />
            Sign in
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setFormError(null);
            }}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition border",
              mode === "signup"
                ? "nc-border-accent nc-bg-accent-20 nc-accent"
                : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-500"
            )}
          >
            <UserPlus className="h-4 w-4" />
            Sign up
          </button>
        </div>

        <p className="text-xs font-medium text-neutral-400 uppercase tracking-wide mb-2">
          Role
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 mb-6">
          {ROLES_LIST.map((r) => {
            const Icon = roleIcon[r];
            const active = role === r;
            return (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-lg border px-2 py-2.5 text-center text-[11px] font-medium transition",
                  active
                    ? "nc-border-accent nc-bg-accent-20 nc-accent"
                    : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-orange-500/50"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {ROLE_LABELS[r]}
              </button>
            );
          })}
        </div>

        <form
          className="flex flex-col gap-4"
          onSubmit={handleSubmit}
          noValidate
        >
          {mode === "signup" && (
            <div>
              <label htmlFor="nc-name" className="block text-sm mb-2 font-medium text-neutral-300">
                Full name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
                <input
                  id="nc-name"
                  type="text"
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Dr. Mehta"
                  className={cn(
                    "text-sm w-full py-2.5 pl-10 pr-3 border rounded-lg focus:outline-none focus:ring-2 bg-neutral-900 text-white placeholder:text-neutral-500 focus:ring-orange-500/40 focus:border-orange-500",
                    fieldErrors.name ? "border-red-500" : "border-neutral-700"
                  )}
                />
              </div>
              {fieldErrors.name && (
                <p className="text-red-500 text-xs mt-1">{fieldErrors.name}</p>
              )}
            </div>
          )}

          <div>
            <label htmlFor="nc-email" className="block text-sm mb-2 font-medium text-neutral-300">
              Your email
            </label>
            <input
              type="email"
              id="nc-email"
              autoComplete="email"
              placeholder="you@hospital.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!fieldErrors.email}
              className={cn(
                "text-sm w-full py-2 px-3 border rounded-lg focus:outline-none focus:ring-2 bg-neutral-900 text-white placeholder:text-neutral-500 focus:ring-orange-500/40 focus:border-orange-500",
                fieldErrors.email ? "border-red-500" : "border-neutral-700"
              )}
            />
            {fieldErrors.email && (
              <p id="nc-email-err" className="text-red-500 text-xs mt-1">
                {fieldErrors.email}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="nc-password" className="block text-sm mb-2 font-medium text-neutral-300">
              {mode === "signup" ? "Create password" : "Password"}
            </label>
            <div className="relative">
              <input
                type="password"
                id="nc-password"
                autoComplete={
                  mode === "signin" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={cn(
                  "text-sm w-full py-2.5 pl-3 pr-3 border rounded-lg focus:outline-none focus:ring-2 bg-neutral-900 text-white placeholder:text-neutral-500 focus:ring-orange-500/40 focus:border-orange-500",
                  fieldErrors.password
                    ? "border-red-500"
                    : "border-neutral-700"
                )}
              />
            </div>
            {fieldErrors.password && (
              <p className="text-red-500 text-xs mt-1">{fieldErrors.password}</p>
            )}
          </div>

          {mode === "signup" && (
            <div>
              <label
                htmlFor="nc-confirm"
                className="block text-sm mb-2 font-medium text-neutral-300"
              >
                Confirm password
              </label>
              <div className="relative">
                <input
                  type="password"
                  id="nc-confirm"
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={cn(
                    "text-sm w-full py-2.5 pl-3 pr-3 border rounded-lg focus:outline-none focus:ring-2 bg-neutral-900 text-white placeholder:text-neutral-500 focus:ring-orange-500/40 focus:border-orange-500",
                    fieldErrors.confirm
                      ? "border-red-500"
                      : "border-neutral-700"
                  )}
                />
              </div>
              {fieldErrors.confirm && (
                <p className="text-red-500 text-xs mt-1">{fieldErrors.confirm}</p>
              )}
            </div>
          )}

          {formError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {formError}
            </div>
          )}

          <button
            type="submit"
            disabled={pending}
            className="w-full nc-btn-accent disabled:opacity-60 font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {pending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Please wait…
              </>
            ) : mode === "signup" ? (
              <>
                <UserPlus className="h-4 w-4" />
                Create a new account
              </>
            ) : (
              <>
                <LogIn className="h-4 w-4" />
                Sign in
              </>
            )}
          </button>

          <div className="text-center text-neutral-400 text-sm">
            {mode === "signup" ? (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  className="nc-accent font-semibold underline underline-offset-2"
                  onClick={() => {
                    setMode("signin");
                    setFormError(null);
                  }}
                >
                  Sign in
                </button>
              </>
            ) : (
              <>
                New here?{" "}
                <button
                  type="button"
                  className="nc-accent font-semibold underline underline-offset-2"
                  onClick={() => {
                    setMode("signup");
                    setFormError(null);
                  }}
                >
                  Create an account
                </button>
              </>
            )}
          </div>

          <p className="text-center text-xs text-neutral-400">
            Demo: hospital@normclaim.in / Hospital@123 · tpa@normclaim.in /
            Tpa@1234 · finance@normclaim.in / Finance@123
          </p>
        </form>
      </div>
    </div>
  );

  if (embedded) {
    return (
      <div className="min-h-screen flex items-center justify-center overflow-hidden p-4 bg-[#0a0a0a]">
        {card}
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center p-4 animate-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="nc-auth-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-default border-0"
        aria-label="Close auth dialog"
        onClick={close}
      />
      <div className="relative z-10 w-full flex justify-center animate-in">
        {card}
      </div>
    </div>
  );
}
