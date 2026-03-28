This README explains how to integrate the `BeamsBackground` React component into the NormClaim web-dashboard and how to set up a minimal React + TypeScript + Tailwind + shadcn project structure.

Summary

- Files added to the workspace:
  - `components/ui/beams-background.tsx` — the component you provided (TypeScript/TSX).
  - `components/ui/demo.tsx` — tiny demo wrapper that renders `BeamsBackground`.
  - `lib/utils.ts` — small `cn` helper used by the component.

Why these files were added

- shadcn (and many UI kits) default to `components/ui` for shared UI primitives. Keeping the component here makes it compatible with that convention.

Quick checks in your repository

- Your workspace currently appears to be a static HTML project (no `package.json`,`tsconfig.json`, or Tailwind files found). To use this React/TSX component you must convert or create a React app in this repo (Next.js or Vite recommended).

Recommended approach (Next.js with shadcn)

1. Create a Next.js + TypeScript app (recommended for shadcn):

   npx create-next-app@latest ./web-dashboard --ts

2. Install Tailwind and configure (Next.js docs + Tailwind docs):

   cd web-dashboard
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p

   // In tailwind.config.js, add:
   module.exports = {
   content: ["./src/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
   theme: { extend: {} },
   plugins: [],
   }

   // Add to globals.css (styles/globals.css):
   @tailwind base;
   @tailwind components;
   @tailwind utilities;

3. Install shadcn CLI and generate UI (optional, but matches your requirement):

   npm i -D @shadcn/cli
   npx shadcn@latest init

   // This will scaffold `src/components/ui` by default. If you choose Next.js, shadcn assumes `src/components/ui`. If your project root doesn't use `src/`, you can still create `components/ui` — keep consistency with src or root.

4. Install motion dependency

The component imports `motion` from `motion/react`. There are two common options:

- Use the `motion` package (Motion One) which exposes `motion/react`:
  npm install motion

- Or use `framer-motion` (widely used). If you prefer `framer-motion`, change the import in `beams-background.tsx` to:
  import { motion } from 'framer-motion'
  npm install framer-motion

Either is fine; `framer-motion` is more feature-rich and common in React apps.

5. Install other helpful packages

   npm install lucide-react

6. Move the new files into the Next/Vite app

- If your app uses `src/`, place `beams-background.tsx` in `src/components/ui/` and `lib/utils.ts` in `src/lib/utils.ts` or adjust path aliases in `tsconfig.json` (the component currently imports `@/lib/utils`).

7. Path aliases

- If you keep `@/` imports, add to `tsconfig.json`:

  {
  "compilerOptions": {
  "baseUrl": "./",
  "paths": { "@/_": ["src/_"] }
  }
  }

8. Use the component as a background

- In Next.js (app router): in `app/layout.tsx` or a page component wrap your app or a particular page with `<BeamsBackground />`:

  import { BeamsBackground } from '@/components/ui/beams-background'

  export default function Layout({ children }) {
  return (
  <BeamsBackground>
  {children}
  </BeamsBackground>
  )
  }

- Or in Vite/React, place `<BeamsBackground />` at the top level in `App.tsx`.

Notes & edge-cases

- The component declares "use client" which is relevant for Next.js app router. If you use standard React (Vite) you can remove it.
- The component currently uses `@/lib/utils` for `cn`. Either add a `lib/utils.ts` in `src/` and enable `@/` path alias, or change the import to a relative path.
- The canvas uses window.innerWidth / innerHeight. For small devices you may want to clamp the canvas size or lower the number of beams to improve perf.

Commands cheat-sheet (copy & run inside project root)

# Create Next.js + TS app (if you don't already have one)

npx create-next-app@latest ./web-dashboard --ts
cd web-dashboard

# Tailwind

npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn CLI (optional)

npm i -D @shadcn/cli
npx shadcn@latest init

# Motion (choose one)

npm install motion

# or

npm install framer-motion

# lucide icons

npm install lucide-react

If you'd like I can:

- Convert this static HTML repo into a Vite + React + TypeScript + Tailwind project and wire the new component in. (I can scaffold files and show exact commands.)
- Or modify `beams-background.tsx` to import from `framer-motion` instead of `motion/react` so it's compatible with `framer-motion`.

Tell me which path you prefer (Next.js vs Vite), and whether to switch to `framer-motion`. I can then scaffold the full React app in this repo and wire the component up automatically.
