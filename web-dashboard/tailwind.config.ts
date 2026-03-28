import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./index.html",
    "./app.html",
  ],
  theme: {
    extend: {
      keyframes: {
        moveBackground: {
          from: { backgroundPosition: "0% 0%" },
          to: { backgroundPosition: "0% -1000%" },
        },
      },
      animation: {
        moveBackground: "moveBackground 60s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
