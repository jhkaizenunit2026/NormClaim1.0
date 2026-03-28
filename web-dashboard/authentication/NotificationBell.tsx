"use client";

import { Bell } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useAuthDialog } from "@/hooks/useAuthDialog";
import { create } from "zustand";

/* ── Notification store (lightweight, separate from auth) ─── */
interface Notification {
  id: string;
  message: string;
  claimId?: string;
  priority: "info" | "warning" | "urgent";
  read: boolean;
  timestamp: string;
}

interface NotificationStore {
  items: Notification[];
  add: (n: Notification) => void;
  markAllRead: () => void;
  unreadCount: () => number;
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  items: [],
  add: (n) => set((s) => ({ items: [n, ...s.items].slice(0, 50) })),
  markAllRead: () =>
    set((s) => ({ items: s.items.map((i) => ({ ...i, read: true })) })),
  unreadCount: () => get().items.filter((i) => !i.read).length,
}));

/* ── Component ─────────────────────────────────────────────── */
export function NotificationBell() {
  const { user } = useAuthStore();
  const { openLogin } = useAuthDialog();
  const { items, markAllRead, unreadCount } = useNotificationStore();
  const count = unreadCount();

  if (!user) {
    return (
      <button
        onClick={openLogin}
        className="relative p-2 rounded-lg text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        aria-label="Sign in to see notifications"
      >
        <Bell className="h-5 w-5" />
      </button>
    );
  }

  return (
    <div className="relative group">
      <button
        className="relative p-2 rounded-lg text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        aria-label={`${count} unread notifications`}
        onClick={markAllRead}
      >
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {/* Dropdown (hover) */}
      <div className="absolute right-0 top-full mt-1.5 w-72 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-lg overflow-hidden z-50 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-zinc-100 dark:border-zinc-800">
          <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
            Notifications
          </span>
          {count > 0 && (
            <button
              onClick={markAllRead}
              className="text-[10px] text-orange-500 hover:text-orange-600 font-medium"
            >
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-64 overflow-y-auto">
          {items.length === 0 ? (
            <p className="text-xs text-zinc-400 text-center py-6">
              No notifications yet.
            </p>
          ) : (
            items.slice(0, 15).map((item) => (
              <div
                key={item.id}
                className={`flex gap-2.5 px-3 py-2.5 border-b border-zinc-50 dark:border-zinc-800/50 last:border-0 ${
                  !item.read ? "bg-orange-50/50 dark:bg-orange-950/10" : ""
                }`}
              >
                <span
                  className={`mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                    item.priority === "urgent"
                      ? "bg-red-500"
                      : item.priority === "warning"
                      ? "bg-amber-500"
                      : "bg-blue-500"
                  }`}
                />
                <div className="min-w-0">
                  <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-snug">
                    {item.message}
                  </p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">
                    {new Date(item.timestamp).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
