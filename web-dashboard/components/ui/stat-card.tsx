"use client";

import { cn } from "@/lib/utils";

import { LiquidCard, CardContent } from "@/components/ui/liquid-glass-card";

interface StatCardProps {
  value: string;
  label: string;
  className?: string;
}

export default function StatCard({ value, label, className }: StatCardProps) {
  return (
    <LiquidCard className={cn("w-full h-full min-h-[160px] flex flex-col justify-center items-center text-center p-6", className)}>
      <CardContent className="p-0 flex flex-col justify-center items-center h-full relative z-10 w-full overflow-hidden">
        <div className="text-4xl lg:text-5xl font-bold tracking-tight text-white drop-shadow-lg mb-2 z-10">
          {value || "—"}
        </div>
        <div className="text-sm text-neutral-300 uppercase tracking-wider font-semibold z-10 drop-shadow-md">
          {label}
        </div>
      </CardContent>
    </LiquidCard>
  );
}
