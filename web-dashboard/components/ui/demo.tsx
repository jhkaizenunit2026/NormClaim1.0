import { BeamsBackground } from "@/components/ui/beams-background";
import { Component as LiquidGlassShowcase } from "@/components/ui/liquid-glass";

export function BeamsBackgroundDemo() {
  return <BeamsBackground />;
}

/** Use as a secondary Vite entry if you want to preview the liquid-glass full page. */
export function DemoOne() {
  return <LiquidGlassShowcase />;
}
