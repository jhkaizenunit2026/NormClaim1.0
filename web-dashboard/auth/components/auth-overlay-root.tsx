import { useEffect, useState } from "react";
import { FullScreenSignup } from "@/components/ui/full-screen-signup";
import type { AuthMode, RoleCode } from "@/auth/types";
import { ROLES_LIST } from "@/auth/types";

function isRole(s: string | undefined): s is RoleCode {
  return !!s && (ROLES_LIST as string[]).includes(s);
}

/** Listens for `normclaim-open-auth` on window; mounts full-screen auth UI. */
export function AuthOverlayRoot() {
  const [open, setOpen] = useState(false);
  const [initialMode, setInitialMode] = useState<AuthMode>("signin");
  const [initialRole, setInitialRole] = useState<RoleCode | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const ce = e as CustomEvent<{ mode?: string; role?: string }>;
      const mode: AuthMode =
        ce.detail?.mode === "signup" ? "signup" : "signin";
      const role = isRole(ce.detail?.role) ? ce.detail!.role! : null;
      setInitialMode(mode);
      setInitialRole(role);
      setOpen(true);
    };
    window.addEventListener("normclaim-open-auth", handler);
    return () => window.removeEventListener("normclaim-open-auth", handler);
  }, []);

  return (
    <FullScreenSignup
      open={open}
      onOpenChange={setOpen}
      initialMode={initialMode}
      initialRole={initialRole}
    />
  );
}
