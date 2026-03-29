import type { Metadata } from "next";
import { AuthDialog } from "@/components/auth/AuthDialog";
import { Providers } from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Normclaim — TPA & Hospital Claims Management",
  description: "End-to-end claim lifecycle management from pre-auth to settlement.",
};

/**
 * Root layout
 * - <Providers> syncs Supabase session → Zustand on every page load
 * - <AuthDialog> floats above all content, triggered by any AuthButton / useAuthDialog hook
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-zinc-50 dark:bg-zinc-950 antialiased">
        <Providers>
          {children}
          {/* Global auth dialog — one instance, mounted here, accessible everywhere */}
          <AuthDialog />
        </Providers>
      </body>
    </html>
  );
}
