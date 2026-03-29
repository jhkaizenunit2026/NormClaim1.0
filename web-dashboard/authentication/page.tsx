import { AuthButton } from "@/components/auth/AuthButton";
import { DashboardNav } from "@/components/layout/DashboardNav";

/**
 * Home page — every CTA button triggers the AuthDialog via AuthButton.
 * No routing needed — the dialog floats above this page.
 */
export default function HomePage() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <DashboardNav />

      <main className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-zinc-900 dark:text-white mb-4">
          Claims management,{" "}
          <span className="text-orange-500">from pre-auth to closure.</span>
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 text-lg max-w-xl mx-auto mb-10">
          Normclaim connects hospitals, TPA officers, and finance teams on a
          single real-time platform — 11 stages, zero paperwork chaos.
        </p>

        {/* These buttons open the AuthDialog automatically */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <AuthButton mode="signup" className="px-6 py-2.5 text-base">
            Get started free
          </AuthButton>
          <AuthButton variant="outline" mode="login" className="px-6 py-2.5 text-base">
            Sign in
          </AuthButton>
        </div>

        {/* Feature cards — each protected button shows auth dialog */}
        <div className="mt-20 grid sm:grid-cols-3 gap-4 text-left">
          {[
            {
              color: "bg-teal-50 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800",
              dot: "bg-teal-500",
              title: "Hospital Portal",
              desc: "Submit pre-auths, upload discharge docs, track approvals in real time.",
              cta: "Start a claim",
              mode: "signup" as const,
            },
            {
              color: "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
              dot: "bg-amber-500",
              title: "TPA Dashboard",
              desc: "Review cases, approve enhancements, and issue settlement letters.",
              cta: "Open queue",
              mode: "login" as const,
            },
            {
              color: "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
              dot: "bg-blue-500",
              title: "Finance Panel",
              desc: "Record ledger entries, track UTRs, and run TDS reconciliation.",
              cta: "View finance",
              mode: "login" as const,
            },
          ].map(({ color, dot, title, desc, cta, mode }) => (
            <div
              key={title}
              className={`rounded-xl border p-5 flex flex-col gap-3 ${color}`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
                <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  {title}
                </h3>
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed flex-1">
                {desc}
              </p>
              {/* AuthButton — opens dialog on click */}
              <AuthButton
                variant="ghost"
                mode={mode}
                className="text-xs justify-start px-0 text-orange-500 hover:text-orange-600 hover:bg-transparent"
              >
                {cta} →
              </AuthButton>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
