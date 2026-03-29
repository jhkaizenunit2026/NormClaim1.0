import type { RoleCode } from "@/auth/types";
import { DEFAULT_DISPLAY_NAMES, ROLE_LABELS } from "@/auth/types";

declare global {
  interface Window {
    NormClaimAuthBridge?: {
      login: (a: {
        email: string;
        password: string;
        role?: string;
        name?: string;
      }) => Promise<unknown>;
      signUp: (a: {
        email: string;
        password: string;
        name: string;
        role: string;
      }) => Promise<unknown>;
    };
    Router?: { navigate: (path: string) => void };
    showToast?: (msg: string, type?: string) => void;
  }
}

function navigateAfterLogin(role: RoleCode) {
  const nav = window.Router?.navigate;
  if (!nav) return;
  if (role === "HOSPITAL") nav("portal/cases");
  else if (role === "TPA") nav("tpa/queue");
  else nav("finance/alerts");
}

export async function signInWithRole(
  email: string,
  password: string,
  role: RoleCode
) {
  const bridge = window.NormClaimAuthBridge;
  if (!bridge) throw new Error("Authentication is not ready. Refresh the page.");

  const name = DEFAULT_DISPLAY_NAMES[role];
  await bridge.login({ email, password, role, name });
  window.showToast?.(`Signed in — ${ROLE_LABELS[role]}`, "success");
  navigateAfterLogin(role);
}

export async function signUpAccount(
  email: string,
  password: string,
  name: string,
  role: RoleCode
) {
  const bridge = window.NormClaimAuthBridge;
  if (!bridge) throw new Error("Authentication is not ready. Refresh the page.");

  await bridge.signUp({ email, password, name, role });
  window.showToast?.("Account created. You are signed in.", "success");
  navigateAfterLogin(role);
}
