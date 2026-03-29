import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthUser, AuthDialogState, AuthMode } from "@/types/auth";
import { supabase } from "@/lib/supabase";

interface AuthStore {
  user: AuthUser | null;
  isLoading: boolean;
  dialog: AuthDialogState;

  // Dialog controls
  openAuthDialog: (mode?: AuthMode) => void;
  closeAuthDialog: () => void;
  setDialogMode: (mode: AuthMode) => void;

  // Auth actions
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string, role: AuthUser["role"]) => Promise<void>;
  loginWithProvider: (provider: "google" | "github" | "azure") => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: AuthUser | null) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      dialog: { isOpen: false, mode: "login" },

      openAuthDialog: (mode = "login") =>
        set({ dialog: { isOpen: true, mode } }),

      closeAuthDialog: () =>
        set((s) => ({ dialog: { ...s.dialog, isOpen: false } })),

      setDialogMode: (mode) =>
        set((s) => ({ dialog: { ...s.dialog, mode } })),

      setUser: (user) => set({ user }),

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
          });
          if (error) throw error;

          // Fetch profile from your DB after login
          const { data: profile } = await supabase
            .from("profiles")
            .select("*")
            .eq("id", data.user.id)
            .single();

          set({
            user: {
              id: data.user.id,
              email: data.user.email!,
              name: profile?.name ?? email.split("@")[0],
              role: profile?.role ?? "HOSPITAL",
              hospitalId: profile?.hospital_id,
              tpaOfficerId: profile?.tpa_officer_id,
              financeUserId: profile?.finance_user_id,
              avatarUrl: profile?.avatar_url,
            },
            isLoading: false,
          });
          get().closeAuthDialog();
        } catch (err: unknown) {
          set({ isLoading: false });
          throw err;
        }
      },

      signup: async (email, password, name, role) => {
        set({ isLoading: true });
        try {
          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: { data: { name, role } },
          });
          if (error) throw error;

          // Insert profile row
          if (data.user) {
            await supabase.from("profiles").insert({
              id: data.user.id,
              email,
              name,
              role,
            });
          }

          set({
            user: {
              id: data.user!.id,
              email,
              name,
              role,
            },
            isLoading: false,
          });
          get().closeAuthDialog();
        } catch (err: unknown) {
          set({ isLoading: false });
          throw err;
        }
      },

      loginWithProvider: async (provider) => {
        set({ isLoading: true });
        try {
          const { error } = await supabase.auth.signInWithOAuth({
            provider,
            options: {
              redirectTo: `${window.location.origin}/auth/callback`,
            },
          });
          if (error) throw error;
        } catch (err) {
          set({ isLoading: false });
          throw err;
        }
      },

      logout: async () => {
        await supabase.auth.signOut();
        set({ user: null });
      },
    }),
    {
      name: "normclaim-auth",
      partialize: (s) => ({ user: s.user }),
    }
  )
);
