"use client";

import { SunIcon as Sunburst } from "lucide-react";
import { useState } from "react";
import { useAuthStore } from "@/store/authStore";

export const FullScreenSignup = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [serverError, setServerError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const { signup, isLoading } = useAuthStore();

  const validateEmail = (value: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const validatePassword = (value: string) => value.length >= 8;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    let valid = true;
    setServerError("");

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    } else {
      setEmailError("");
    }

    if (!validatePassword(password)) {
      setPasswordError("Password must be at least 8 characters.");
      valid = false;
    } else {
      setPasswordError("");
    }

    setSubmitted(true);

    if (valid) {
      try {
        await signup(email, password, email.split("@")[0], "HOSPITAL");
        setEmail("");
        setPassword("");
        setSubmitted(false);
      } catch (err: unknown) {
        setServerError(
          err instanceof Error ? err.message : "Something went wrong."
        );
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center overflow-hidden p-4">
      <div className="w-full relative max-w-5xl overflow-hidden flex flex-col md:flex-row shadow-xl rounded-2xl">
        {/* overlay */}
        <div className="w-full h-full z-[2] absolute bg-gradient-to-t from-transparent to-black pointer-events-none rounded-2xl" />

        {/* stripe blur overlay */}
        <div className="flex absolute z-[2] overflow-hidden backdrop-blur-2xl pointer-events-none">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-[40rem] z-[2] w-[4rem] opacity-30 overflow-hidden"
              style={{
                background:
                  "linear-gradient(90deg, #ffffff00, #000000 69%, #ffffff30)",
              }}
            />
          ))}
        </div>

        {/* decorative blobs */}
        <div className="w-60 h-60 bg-orange-500 absolute z-[1] rounded-full -bottom-10 -left-10 opacity-60 blur-2xl" />
        <div className="w-32 h-20 bg-white absolute z-[1] rounded-full bottom-0 opacity-20" />

        {/* LEFT — branding */}
        <div className="bg-black text-white p-8 md:p-12 md:w-1/2 relative rounded-bl-3xl overflow-hidden">
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-6">
              <Sunburst className="h-7 w-7 text-orange-500" />
              <span className="text-base font-semibold tracking-tight">
                Normclaim
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-medium leading-tight tracking-tight">
              The complete TPA &amp; Hospital claims management platform.
            </h1>
            <div className="mt-8 space-y-3">
              {[
                { color: "bg-teal-400", text: "Pre-auth to admission" },
                { color: "bg-amber-400", text: "Enhancement & discharge" },
                { color: "bg-blue-400", text: "Settlement & finance" },
                { color: "bg-green-400", text: "Full audit trail" },
              ].map(({ color, text }) => (
                <div
                  key={text}
                  className="flex items-center gap-3 text-sm text-white/70"
                >
                  <span className={`w-2 h-2 rounded-full ${color}`} />
                  {text}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT — form */}
        <div className="p-8 md:p-12 md:w-1/2 flex flex-col bg-zinc-100 dark:bg-zinc-900 z-[99] text-zinc-900 dark:text-white relative">
          <div className="flex flex-col items-start mb-8">
            <div className="text-orange-500 mb-4">
              <Sunburst className="h-10 w-10" />
            </div>
            <h2 className="text-3xl font-medium mb-2 tracking-tight">
              Get Started
            </h2>
            <p className="text-sm opacity-70">
              Welcome to Normclaim — let&apos;s create your account
            </p>
          </div>

          {serverError && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {serverError}
            </div>
          )}

          <form
            className="flex flex-col gap-4"
            onSubmit={handleSubmit}
            noValidate
          >
            <div>
              <label htmlFor="su-email" className="block text-sm mb-2">
                Your email
              </label>
              <input
                type="email"
                id="su-email"
                placeholder="you@hospital.org"
                className={`text-sm w-full py-2 px-3 border rounded-lg focus:outline-none focus:ring-1 bg-white text-black focus:ring-orange-500 ${
                  emailError ? "border-red-500" : "border-gray-300"
                }`}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={!!emailError}
                aria-describedby="su-email-error"
              />
              {emailError && (
                <p id="su-email-error" className="text-red-500 text-xs mt-1">
                  {emailError}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="su-password" className="block text-sm mb-2">
                Create password
              </label>
              <input
                type="password"
                id="su-password"
                placeholder="Min. 8 characters"
                className={`text-sm w-full py-2 px-3 border rounded-lg focus:outline-none focus:ring-1 bg-white text-black focus:ring-orange-500 ${
                  passwordError ? "border-red-500" : "border-gray-300"
                }`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={!!passwordError}
                aria-describedby="su-password-error"
              />
              {passwordError && (
                <p
                  id="su-password-error"
                  className="text-red-500 text-xs mt-1"
                >
                  {passwordError}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-orange-500 hover:bg-orange-600 disabled:opacity-60 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {isLoading && (
                <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              Create my account
            </button>

            <div className="text-center text-gray-500 text-sm">
              Already have an account?{" "}
              <a
                href="/login"
                className="text-orange-500 font-medium hover:underline"
              >
                Sign in
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
