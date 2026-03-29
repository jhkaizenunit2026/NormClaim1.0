"use client";

import { useState, useEffect, useRef } from "react";
import { SunIcon as Sunburst, X, Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import type { AuthMode } from "@/types/auth";

/* ─── tiny helpers ────────────────────────────────────────────── */
const validateEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
const validatePassword = (v: string) => v.length >= 8;

/* ─── Google icon SVG ─────────────────────────────────────────── */
const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

/* ─── GitHub icon SVG ─────────────────────────────────────────── */
const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden>
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
  </svg>
);

/* ─── Role selector ───────────────────────────────────────────── */
const ROLES = [
  { value: "HOSPITAL", label: "Hospital", desc: "Clinical staff, admin" },
  { value: "TPA", label: "TPA Officer", desc: "Claims processing" },
  { value: "FINANCE", label: "Finance", desc: "Settlement & ledger" },
] as const;

/* ═══════════════════════════════════════════════════════════════ */
/*  AUTH DIALOG                                                    */
/* ═══════════════════════════════════════════════════════════════ */
export function AuthDialog() {
  const { dialog, closeAuthDialog, setDialogMode, login, signup, loginWithProvider, isLoading } =
    useAuthStore();
  const { isOpen, mode } = dialog;

  /* form state */
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<"HOSPITAL" | "TPA" | "FINANCE">("HOSPITAL");
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement>(null);

  /* reset when dialog opens / mode changes */
  useEffect(() => {
    if (isOpen) {
      setEmail(""); setPassword(""); setName("");
      setErrors({}); setServerError(""); setShowPw(false);
      setTimeout(() => emailRef.current?.focus(), 80);
    }
  }, [isOpen, mode]);

  /* close on Escape */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") closeAuthDialog(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [closeAuthDialog]);

  if (!isOpen) return null;

  /* ── validation ─────────────────────────────────────────────── */
  const validate = () => {
    const e: Record<string, string> = {};
    if (!validateEmail(email)) e.email = "Enter a valid email address.";
    if (mode !== "forgot") {
      if (!validatePassword(password)) e.password = "Password must be at least 8 characters.";
    }
    if (mode === "signup" && !name.trim()) e.name = "Full name is required.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  /* ── submit ─────────────────────────────────────────────────── */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");
    if (!validate()) return;
    try {
      if (mode === "login") await login(email, password);
      else if (mode === "signup") await signup(email, password, name, role);
      else {
        // forgot password — use supabase directly
        const { supabase } = await import("@/lib/supabase");
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/auth/reset`,
        });
        if (error) throw error;
        setServerError(""); // clear
        alert("Password reset email sent! Check your inbox.");
        closeAuthDialog();
      }
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  };

  /* ── OAuth ──────────────────────────────────────────────────── */
  const handleOAuth = async (provider: "google" | "github" | "azure") => {
    setOauthLoading(provider);
    setServerError("");
    try {
      await loginWithProvider(provider);
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "OAuth sign-in failed.");
      setOauthLoading(null);
    }
  };

  /* ── UI ─────────────────────────────────────────────────────── */
  const switchMode = (m: AuthMode) => { setDialogMode(m); setErrors({}); setServerError(""); };

  const titles: Record<AuthMode, { h: string; sub: string }> = {
    login:  { h: "Welcome back",      sub: "Sign in to your Normclaim account" },
    signup: { h: "Create account",    sub: "Join Normclaim — it's free to start" },
    forgot: { h: "Reset password",    sub: "We'll send a reset link to your email" },
  };

  return (
    /* ── Backdrop ───────────────────────────────────────────── */
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(6px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) closeAuthDialog(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Authentication"
    >
      {/* ── Dialog card ──────────────────────────────────────── */}
      <div
        className="relative w-full max-w-4xl overflow-hidden rounded-2xl shadow-2xl flex flex-col md:flex-row"
        style={{ maxHeight: "90vh" }}
      >
        {/* ── LEFT PANEL — branding ─────────────────────────── */}
        <div className="hidden md:flex md:w-5/12 flex-col justify-between bg-black text-white p-10 relative overflow-hidden">
          {/* decorative blobs */}
          <div className="absolute bottom-0 left-0 w-56 h-56 rounded-full bg-orange-500 opacity-20 blur-3xl pointer-events-none" />
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-orange-400 opacity-10 blur-2xl pointer-events-none" />

          {/* logo */}
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-8">
              <Sunburst className="h-7 w-7 text-orange-500" />
              <span className="text-lg font-semibold tracking-tight">Normclaim</span>
            </div>
            <h2 className="text-2xl font-medium leading-snug tracking-tight text-white/90">
              The complete TPA &amp; Hospital claims management platform.
            </h2>
          </div>

          {/* stage callouts */}
          <div className="relative z-10 space-y-3 mt-8">
            {[
              { color: "bg-teal-500",   label: "Pre-auth to admission" },
              { color: "bg-amber-500",  label: "Enhancement & discharge" },
              { color: "bg-blue-500",   label: "Settlement & finance" },
              { color: "bg-green-500",  label: "Full audit trail" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-3 text-sm text-white/70">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${color}`} />
                {label}
              </div>
            ))}
          </div>

          <p className="relative z-10 text-xs text-white/30 mt-6">
            © {new Date().getFullYear()} Normclaim. All rights reserved.
          </p>
        </div>

        {/* ── RIGHT PANEL — form ────────────────────────────── */}
        <div className="flex-1 bg-white dark:bg-zinc-950 flex flex-col overflow-y-auto">
          {/* close button */}
          <button
            onClick={closeAuthDialog}
            className="absolute top-4 right-4 z-10 p-1.5 rounded-full text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>

          <div className="flex-1 p-8 md:p-10 flex flex-col justify-center">
            {/* mobile logo */}
            <div className="flex md:hidden items-center gap-2 mb-6">
              <Sunburst className="h-6 w-6 text-orange-500" />
              <span className="text-base font-semibold tracking-tight text-zinc-900 dark:text-white">
                Normclaim
              </span>
            </div>

            {/* heading */}
            <div className="mb-6">
              <h3 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-white">
                {titles[mode].h}
              </h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                {titles[mode].sub}
              </p>
            </div>

            {/* ── OAuth buttons (not on forgot) ─────────────── */}
            {mode !== "forgot" && (
              <>
                <div className="flex flex-col gap-2 mb-5">
                  <button
                    type="button"
                    onClick={() => handleOAuth("google")}
                    disabled={!!oauthLoading || isLoading}
                    className="flex items-center justify-center gap-2.5 w-full py-2 px-4 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
                  >
                    {oauthLoading === "google"
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : <GoogleIcon />}
                    Continue with Google
                  </button>

                  <button
                    type="button"
                    onClick={() => handleOAuth("github")}
                    disabled={!!oauthLoading || isLoading}
                    className="flex items-center justify-center gap-2.5 w-full py-2 px-4 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
                  >
                    {oauthLoading === "github"
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : <GitHubIcon />}
                    Continue with GitHub
                  </button>
                </div>

                {/* divider */}
                <div className="flex items-center gap-3 mb-5">
                  <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
                  <span className="text-xs text-zinc-400">or continue with email</span>
                  <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
                </div>
              </>
            )}

            {/* ── Server error ───────────────────────────────── */}
            {serverError && (
              <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>{serverError}</span>
              </div>
            )}

            {/* ── FORM ──────────────────────────────────────── */}
            <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>

              {/* Name (signup only) */}
              {mode === "signup" && (
                <div>
                  <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1.5">
                    Full name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dr. Aryan Sharma"
                    className={`w-full text-sm py-2.5 px-3 rounded-lg border bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-colors ${
                      errors.name
                        ? "border-red-400 dark:border-red-600"
                        : "border-zinc-200 dark:border-zinc-700"
                    }`}
                    aria-invalid={!!errors.name}
                  />
                  {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name}</p>}
                </div>
              )}

              {/* Email */}
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1.5">
                  Email address
                </label>
                <input
                  ref={emailRef}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@hospital.org"
                  className={`w-full text-sm py-2.5 px-3 rounded-lg border bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-colors ${
                    errors.email
                      ? "border-red-400 dark:border-red-600"
                      : "border-zinc-200 dark:border-zinc-700"
                  }`}
                  aria-invalid={!!errors.email}
                />
                {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email}</p>}
              </div>

              {/* Password (not on forgot) */}
              {mode !== "forgot" && (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                      Password
                    </label>
                    {mode === "login" && (
                      <button
                        type="button"
                        onClick={() => switchMode("forgot")}
                        className="text-xs text-orange-500 hover:text-orange-600 font-medium"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={showPw ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={mode === "signup" ? "Min. 8 characters" : "••••••••"}
                      className={`w-full text-sm py-2.5 px-3 pr-10 rounded-lg border bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-colors ${
                        errors.password
                          ? "border-red-400 dark:border-red-600"
                          : "border-zinc-200 dark:border-zinc-700"
                      }`}
                      aria-invalid={!!errors.password}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((p) => !p)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                      tabIndex={-1}
                      aria-label={showPw ? "Hide password" : "Show password"}
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password}</p>}
                </div>
              )}

              {/* Role selector (signup only) */}
              {mode === "signup" && (
                <div>
                  <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1.5">
                    Your role
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {ROLES.map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() => setRole(r.value)}
                        className={`flex flex-col items-center p-2.5 rounded-lg border text-center transition-all text-xs ${
                          role === r.value
                            ? "border-orange-500 bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400"
                            : "border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:border-zinc-300 dark:hover:border-zinc-600"
                        }`}
                      >
                        <span className="font-medium">{r.label}</span>
                        <span className="text-[10px] opacity-70 mt-0.5">{r.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading || !!oauthLoading}
                className="mt-1 w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 active:bg-orange-700 text-white text-sm font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {mode === "login" && "Sign in to Normclaim"}
                {mode === "signup" && "Create my account"}
                {mode === "forgot" && "Send reset link"}
              </button>
            </form>

            {/* ── Mode switcher ─────────────────────────────── */}
            <div className="mt-5 text-center text-xs text-zinc-500 dark:text-zinc-400">
              {mode === "login" && (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("signup")}
                    className="text-orange-500 hover:text-orange-600 font-medium"
                  >
                    Sign up free
                  </button>
                </>
              )}
              {mode === "signup" && (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => switchMode("login")}
                    className="text-orange-500 hover:text-orange-600 font-medium"
                  >
                    Sign in
                  </button>
                </>
              )}
              {mode === "forgot" && (
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                  className="text-orange-500 hover:text-orange-600 font-medium"
                >
                  ← Back to sign in
                </button>
              )}
            </div>

            {/* ── Legal ─────────────────────────────────────── */}
            {mode === "signup" && (
              <p className="mt-4 text-center text-[10px] text-zinc-400 dark:text-zinc-600">
                By creating an account you agree to our{" "}
                <a href="/terms" className="underline hover:text-zinc-600">Terms of Service</a>
                {" "}and{" "}
                <a href="/privacy" className="underline hover:text-zinc-600">Privacy Policy</a>.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
