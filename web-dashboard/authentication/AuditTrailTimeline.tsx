import { CLAIM_STATUS_LABEL } from "@/constants/claimStatus";
import type { ClaimStatus } from "@/constants/claimStatus";

export interface AuditEntry {
  id: string;
  timestamp: string;        // ISO string
  actorName: string;
  actorRole: string;
  action: string;           // e.g. "Pre-auth approved — ₹45,000"
  stage: ClaimStatus;
}

interface AuditTrailTimelineProps {
  entries: AuditEntry[];
  className?: string;
}

const formatTime = (iso: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: true,
  }).format(new Date(iso));

const ROLE_COLOR: Record<string, string> = {
  HOSPITAL: "text-teal-600 dark:text-teal-400",
  TPA:      "text-amber-600 dark:text-amber-400",
  FINANCE:  "text-blue-600 dark:text-blue-400",
};

export function AuditTrailTimeline({ entries, className = "" }: AuditTrailTimelineProps) {
  if (!entries.length) {
    return (
      <div className={`text-sm text-zinc-400 text-center py-6 ${className}`}>
        No audit entries yet.
      </div>
    );
  }

  return (
    <ol className={`relative border-l border-zinc-200 dark:border-zinc-700 ml-3 ${className}`}>
      {entries.map((entry, idx) => (
        <li key={entry.id} className="mb-6 ml-5 last:mb-0">
          {/* dot */}
          <span className="absolute -left-2 flex h-4 w-4 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900/40 ring-4 ring-white dark:ring-zinc-950">
            <span className="h-1.5 w-1.5 rounded-full bg-orange-500" />
          </span>

          {/* stage label */}
          <p className="text-[10px] font-medium text-zinc-400 dark:text-zinc-500 mb-0.5 uppercase tracking-wide">
            Stage {idx + 1} · {CLAIM_STATUS_LABEL[entry.stage]}
          </p>

          {/* action */}
          <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
            {entry.action}
          </p>

          {/* actor + time */}
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            <span className={`font-medium ${ROLE_COLOR[entry.actorRole] ?? ""}`}>
              {entry.actorName}
            </span>
            {" · "}
            <span>{entry.actorRole}</span>
            {" · "}
            <time dateTime={entry.timestamp}>{formatTime(entry.timestamp)}</time>
          </p>
        </li>
      ))}
    </ol>
  );
}
