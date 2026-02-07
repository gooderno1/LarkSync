import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        lark: {
          DEFAULT: "#3370FF",
          hover: "#5b8eff",
          light: "rgba(51, 112, 255, 0.15)",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Cascadia Code", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
        xl: "0.75rem",
        lg: "0.5rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
