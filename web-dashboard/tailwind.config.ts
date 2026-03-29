import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./auth/**/*.{ts,tsx}",
    "./index.html",
    "./app.html",
  ],
  theme: {
    extend: {
      colors: {
        secondary: {
          DEFAULT: "#f4f4f5",
          foreground: "#18181b",
        },
      },
      keyframes: {
        moveBackground: {
          from: { backgroundPosition: "0% 0%" },
          to: { backgroundPosition: "0% -1000%" },
        },
        shimmer2: {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "-200% 0%" },
        },
      },
      animation: {
        moveBackground: "moveBackground 60s linear infinite",
        shimmer2: "shimmer2 2s infinite linear",
      },
    },
  },
  plugins: [],
} satisfies Config;
