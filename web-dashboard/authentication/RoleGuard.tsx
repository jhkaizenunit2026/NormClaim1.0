"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import type { UserRole } from "@/types/auth";

interface RoleGuardProps {
  /** Roles allowed to view this route */
  allow: UserRole | UserRole[];
  /** Fallback while auth is being resolved */
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * RoleGuard
 * Wrap any page or section. Opens auth dialog if unauthenticated.
 * Renders a "403" message if authenticated but wrong role.
 *
 * Usage:
 *   <RoleGuard allow="TPA">
 *     <DischargeApprovalPanel />
 *   </RoleGuard>
 *
 *   <RoleGuard allow={["HOSPITAL", "TPA"]}>
 *     <ClaimDetailPage />
 *   </RoleGuard>
 */
export function RoleGuard({ allow, fallback, children }: RoleGuardProps) {
  const { user, isLoading, openAuthDialog } = useAuthStore();
  const allowed = Array.isArray(allow) ? allow : [allow];

  useEffect(() => {
    if (!isLoading && !user) {
      openAuthDialog("login");
    }
  }, [isLoading, user, openAuthDialog]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-32">
        <span className="h-6 w-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return fallback ? (
      <>{fallback}</>
    ) : (
      <div className="flex flex-col items-center justify-center min-h-64 gap-3 text-center">
        <p className="text-zinc-500 text-sm">
          You must be signed in to view this page.
        </p>
      </div>
    );
  }

  if (!allowed.includes(user.role)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-64 gap-2 text-center">
        <p className="text-2xl font-semibold text-zinc-800 dark:text-zinc-200">
          403
        </p>
        <p className="text-zinc-500 text-sm">
          Your role ({user.role}) does not have access to this section.
        </p>
        <p className="text-xs text-zinc-400">
          Required: {allowed.join(" or ")}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
