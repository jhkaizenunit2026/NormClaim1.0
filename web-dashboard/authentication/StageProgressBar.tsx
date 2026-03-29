"use client";

import { Check } from "lucide-react";
import { CLAIM_STATUS, isAtOrPast } from "@/constants/claimStatus";
import type { ClaimStatus } from "@/constants/claimStatus";
import type { UserRole } from "@/types/auth";

const ALL_STAGES: { status: ClaimStatus; label: string; short: string }[] = [
  { status: "PRE_AUTH_INITIATED",    label: "Pre-auth initiated",    short: "Pre-auth"    },
  { status: "PRE_AUTH_APPROVED",     label: "Pre-auth approved",     short: "Approved"    },
  { status: "ADMITTED",              label: "Admitted",              short: "Admitted"    },
  { status: "ENHANCEMENT_REQUESTED", label: "Enhancement requested", short: "Enhance"     },
  { status: "ENHANCEMENT_APPROVED",  label: "Enhancement approved",  short: "Enhanced"    },
  { status: "DISCHARGE_INTIMATED",   label: "Discharge intimated",   short: "Discharge"   },
  { status: "DISCHARGE_APPROVED",    label: "Discharge approved",    short: "D. Approved" },
  { status: "DISCHARGE_COMPLETE",    label: "Discharge complete",    short: "Discharged"  },
  { status: "SETTLEMENT_ISSUED",     label: "Settlement issued",     short: "Settlement"  },
  { status: "FINANCE_PROCESSED",     label: "Finance processed",     short: "Finance"     },
  { status: "CLOSED",                label: "Closed",                short: "Closed"      },
];

// Finance role only sees stages 9–11
const FINANCE_STAGES = ALL_STAGES.slice(8);

const STAGE_COLORS: Partial<Record<ClaimStatus, string>> = {
  PRE_AUTH_INITIATED:    "bg-teal-500",
  PRE_AUTH_APPROVED:     "bg-teal-500",
  ADMITTED:              "bg-teal-500",
  ENHANCEMENT_REQUESTED: "bg-amber-500",
  ENHANCEMENT_APPROVED:  "bg-amber-500",
  DISCHARGE_INTIMATED:   "bg-orange-500",
  DISCHARGE_APPROVED:    "bg-orange-500",
  DISCHARGE_COMPLETE:    "bg-orange-500",
  SETTLEMENT_ISSUED:     "bg-blue-500",
  FINANCE_PROCESSED:     "bg-blue-500",
  CLOSED:                "bg-green-500",
};

interface StageProgressBarProps {
  currentStatus: ClaimStatus;
  role: UserRole;
  onStageClick?: (status: ClaimStatus) => void;
  className?: string;
}

export function StageProgressBar({
  currentStatus,
  role,
  onStageClick,
  className = "",
}: StageProgressBarProps) {
  const stages = role === "FINANCE" ? FINANCE_STAGES : ALL_STAGES;
  const currentIndex = stages.findIndex((s) => s.status === currentStatus);

  return (
    <div className={`w-full ${className}`}>
      {/* Progress bar track */}
      <div className="relative flex items-center">
        {stages.map((stage, idx) => {
          const isDone = isAtOrPast(currentStatus, stage.status);
          const isCurrent = stage.status === currentStatus;
          const color = STAGE_COLORS[stage.status] ?? "bg-zinc-400";
          const isLast = idx === stages.length - 1;

          return (
            <div key={stage.status} className="flex items-center flex-1 min-w-0">
              {/* Node */}
              <button
                type="button"
                title={stage.label}
                onClick={() => onStageClick?.(stage.status)}
                disabled={!isDone}
                className={`relative flex-shrink-0 h-7 w-7 rounded-full flex items-center justify-center text-xs font-medium transition-all
                  ${isDone ? `${color} text-white shadow-sm` : "bg-zinc-200 dark:bg-zinc-700 text-zinc-400"}
                  ${isCurrent ? "ring-2 ring-offset-2 ring-orange-400 scale-110" : ""}
                  ${isDone && onStageClick ? "cursor-pointer hover:opacity-80" : "cursor-default"}
                `}
              >
                {isDone && !isCurrent ? (
                  <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                ) : (
                  <span>{idx + 1 + (role === "FINANCE" ? 8 : 0)}</span>
                )}
              </button>

              {/* Connector line */}
              {!isLast && (
                <div className="flex-1 h-0.5 mx-1 min-w-0">
                  <div
                    className={`h-full transition-all duration-500 ${
                      isAtOrPast(currentStatus, stages[idx + 1].status)
                        ? `${color}`
                        : "bg-zinc-200 dark:bg-zinc-700"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Current stage label */}
      <div className="mt-2 text-center">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          {stages[currentIndex]?.label ?? "Unknown stage"}
        </span>
        <span className="text-xs text-zinc-400 dark:text-zinc-600 ml-1.5">
          ({currentIndex + 1} of {stages.length})
        </span>
      </div>
    </div>
  );
}
