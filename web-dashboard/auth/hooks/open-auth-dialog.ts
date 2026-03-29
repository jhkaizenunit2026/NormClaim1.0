import type { AuthMode, RoleCode } from "@/auth/types";

/** Fire from React/TS code to open the full-screen auth overlay. */
export function openNormClaimAuthDialog(
  mode: AuthMode = "signin",
  role?: RoleCode | null
) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<{ mode: AuthMode; role?: RoleCode | null }>(
      "normclaim-open-auth",
      { detail: { mode, role: role ?? undefined } }
    )
  );
}
