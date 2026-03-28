export type AuthMode = "signin" | "signup";

export type RoleCode = "HOSPITAL" | "TPA" | "FINANCE";

export const ROLES_LIST: RoleCode[] = ["HOSPITAL", "TPA", "FINANCE"];

export const ROLE_LABELS: Record<RoleCode, string> = {
  HOSPITAL: "Hospital Portal",
  TPA: "TPA Dashboard",
  FINANCE: "Finance Panel",
};

export const DEFAULT_DISPLAY_NAMES: Record<RoleCode, string> = {
  HOSPITAL: "Dr. Mehta",
  TPA: "Rahul Sharma",
  FINANCE: "Anita Kapoor",
};
