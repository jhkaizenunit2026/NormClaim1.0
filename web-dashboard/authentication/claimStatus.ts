export const CLAIM_STATUS = {
  PRE_AUTH_INITIATED:    "PRE_AUTH_INITIATED",
  PRE_AUTH_APPROVED:     "PRE_AUTH_APPROVED",
  ADMITTED:              "ADMITTED",
  ENHANCEMENT_REQUESTED: "ENHANCEMENT_REQUESTED",
  ENHANCEMENT_APPROVED:  "ENHANCEMENT_APPROVED",
  DISCHARGE_INTIMATED:   "DISCHARGE_INTIMATED",
  DISCHARGE_APPROVED:    "DISCHARGE_APPROVED",
  DISCHARGE_COMPLETE:    "DISCHARGE_COMPLETE",
  SETTLEMENT_ISSUED:     "SETTLEMENT_ISSUED",
  FINANCE_PROCESSED:     "FINANCE_PROCESSED",
  CLOSED:                "CLOSED",
} as const;

export type ClaimStatus = (typeof CLAIM_STATUS)[keyof typeof CLAIM_STATUS];

const ORDER = Object.values(CLAIM_STATUS);

/** Is the current status at or past the target stage? */
export const isAtOrPast = (current: ClaimStatus, target: ClaimStatus): boolean =>
  ORDER.indexOf(current) >= ORDER.indexOf(target);

/** Is the current status strictly before the target? */
export const isBefore = (current: ClaimStatus, target: ClaimStatus): boolean =>
  ORDER.indexOf(current) < ORDER.indexOf(target);

/** Get the numeric stage index (1-based) */
export const stageNumber = (status: ClaimStatus): number =>
  ORDER.indexOf(status) + 1;

/** Get the next status in the pipeline, or null if closed */
export const nextStatus = (current: ClaimStatus): ClaimStatus | null =>
  ORDER[ORDER.indexOf(current) + 1] ?? null;

/** Human-readable label map */
export const CLAIM_STATUS_LABEL: Record<ClaimStatus, string> = {
  PRE_AUTH_INITIATED:    "Pre-auth initiated",
  PRE_AUTH_APPROVED:     "Pre-auth approved",
  ADMITTED:              "Admitted",
  ENHANCEMENT_REQUESTED: "Enhancement requested",
  ENHANCEMENT_APPROVED:  "Enhancement approved",
  DISCHARGE_INTIMATED:   "Discharge intimated",
  DISCHARGE_APPROVED:    "Discharge approved",
  DISCHARGE_COMPLETE:    "Discharge complete",
  SETTLEMENT_ISSUED:     "Settlement issued",
  FINANCE_PROCESSED:     "Finance processed",
  CLOSED:                "Closed",
};

/** Tailwind color classes by stage group */
export const CLAIM_STATUS_COLOR: Record<ClaimStatus, string> = {
  PRE_AUTH_INITIATED:    "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
  PRE_AUTH_APPROVED:     "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
  ADMITTED:              "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
  ENHANCEMENT_REQUESTED: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
  ENHANCEMENT_APPROVED:  "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
  DISCHARGE_INTIMATED:   "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  DISCHARGE_APPROVED:    "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  DISCHARGE_COMPLETE:    "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  SETTLEMENT_ISSUED:     "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
  FINANCE_PROCESSED:     "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
  CLOSED:                "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
};
