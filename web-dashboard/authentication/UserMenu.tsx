"use client";

import { useState, useRef, useEffect } from "react";
import { LogOut, ChevronDown, User, Settings } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { AuthButton } from "./AuthButton";

const ROLE_COLORS: Record<string, string> = {
  HOSPITAL: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
  TPA:      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
  FINANCE:  "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
};

export function UserMenu() {
  const { user, logout } = useAuthStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <AuthButton variant="ghost" mode="login">Sign in</AuthButton>
        <AuthButton variant="default" mode="signup">Get started</AuthButton>
      </div>
    );
  }

  const initials = user.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
      >
        {/* Avatar */}
        <div className="h-7 w-7 rounded-full bg-orange-500 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
          {user.avatarUrl ? (
            <img src={user.avatarUrl} alt={user.name} className="h-7 w-7 rounded-full object-cover" />
          ) : (
            initials
          )}
        </div>
        <div className="hidden sm:flex flex-col items-start">
          <span className="text-xs font-medium text-zinc-900 dark:text-white leading-none">
            {user.name}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full mt-0.5 font-medium ${ROLE_COLORS[user.role] ?? ""}`}>
            {user.role}
          </span>
        </div>
        <ChevronDown className={`h-3.5 w-3.5 text-zinc-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-52 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-lg overflow-hidden z-50">
          {/* User info header */}
          <div className="px-3 py-2.5 border-b border-zinc-100 dark:border-zinc-800">
            <p className="text-xs font-medium text-zinc-900 dark:text-white">{user.name}</p>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">{user.email}</p>
          </div>

          {/* Menu items */}
          <div className="py-1">
            <button className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
              <User className="h-4 w-4 text-zinc-400" />
              Profile
            </button>
            <button className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
              <Settings className="h-4 w-4 text-zinc-400" />
              Settings
            </button>
          </div>

          <div className="border-t border-zinc-100 dark:border-zinc-800 py-1">
            <button
              onClick={() => { logout(); setOpen(false); }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
