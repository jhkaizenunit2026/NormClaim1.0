"use client";

import { useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/authStore";

/**
 * useSupabaseSession
 * Mount this once at the root (e.g. in a Providers component).
 * Syncs the Supabase session → Zustand user on page load and on auth state changes.
 * Handles OAuth callbacks automatically.
 */
export function useSupabaseSession() {
  const { setUser } = useAuthStore();

  useEffect(() => {
    // Initial session check
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session?.user) { setUser(null); return; }
      const { data: profile } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", session.user.id)
        .single();

      setUser({
        id: session.user.id,
        email: session.user.email!,
        name: profile?.name ?? session.user.email!.split("@")[0],
        role: profile?.role ?? "HOSPITAL",
        hospitalId: profile?.hospital_id,
        tpaOfficerId: profile?.tpa_officer_id,
        financeUserId: profile?.finance_user_id,
        avatarUrl: profile?.avatar_url,
      });
    });

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (!session?.user) { setUser(null); return; }
        if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
          const { data: profile } = await supabase
            .from("profiles")
            .select("*")
            .eq("id", session.user.id)
            .single();

          setUser({
            id: session.user.id,
            email: session.user.email!,
            name: profile?.name ?? session.user.email!.split("@")[0],
            role: profile?.role ?? "HOSPITAL",
            hospitalId: profile?.hospital_id,
            tpaOfficerId: profile?.tpa_officer_id,
            financeUserId: profile?.finance_user_id,
            avatarUrl: profile?.avatar_url,
          });
        }
        if (event === "SIGNED_OUT") setUser(null);
      }
    );

    return () => subscription.unsubscribe();
  }, [setUser]);
}
