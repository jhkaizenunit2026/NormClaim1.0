import { useState } from "react";
import { BeamsBackground } from "@/components/ui/beams-background";
import { Component as LiquidGlassShowcase } from "@/components/ui/liquid-glass";
import { FullScreenSignup } from "@/components/ui/full-screen-signup";

export function BeamsBackgroundDemo() {
  return <BeamsBackground />;
}

/** Liquid glass showcase (full page). */
export function LiquidGlassDemo() {
  return <LiquidGlassShowcase />;
}

function DemoOne() {
  return <FullScreenSignup embedded initialMode="signup" />;
}

export function FullScreenSignupDemo() {
  const [open, setOpen] = useState(true);
  return (
    <div className="min-h-screen bg-[#0a0a0a] p-8">
      <button
        type="button"
        className="rounded-lg bg-orange-500 px-4 py-2 text-white"
        onClick={() => setOpen(true)}
      >
        Open auth modal
      </button>
      <FullScreenSignup
        open={open}
        onOpenChange={setOpen}
        initialMode="signin"
        initialRole="HOSPITAL"
      />
    </div>
  );
}

export default { DemoOne };
