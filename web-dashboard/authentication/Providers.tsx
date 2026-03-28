"use client";

import { useSupabaseSession } from "@/hooks/useSupabaseSession";

/**
 * Providers
 * Client-side wrapper mounted in layout.tsx.
 * Handles Supabase session sync on every page load.
 * Add any other global providers (QueryClientProvider, ThemeProvider) here.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  useSupabaseSession();
  return <>{children}</>;
}
