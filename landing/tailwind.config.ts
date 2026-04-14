import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary:  "var(--color-purple-600)",
        accent:   "var(--color-gold-500)",
        surface:  "var(--color-surface)",
        brand: {
          purple:         "var(--color-purple-600)",
          "purple-dark":  "var(--color-purple-700)",
          "purple-light": "var(--color-purple-50)",
          "purple-bg":    "var(--color-surface-2)",
          gold:           "var(--color-gold-500)",
          "gold-dark":    "var(--color-gold-600)",
          "gold-light":   "var(--color-gold-50)",
          surface:        "var(--color-surface)",
          text:           "var(--color-ink-900)",
          muted:          "var(--color-ink-500)",
          border:         "var(--color-ink-100)",
        },
      },
      fontFamily: {
        sans:    ["var(--font-manrope)", "Manrope", "system-ui", "sans-serif"],
        display: ["var(--font-urbanist)", "Urbanist", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card:         "0 2px 12px 0 rgba(92,45,145,0.08), 0 1px 3px 0 rgba(92,45,145,0.05)",
        "card-hover": "0 8px 24px 0 rgba(92,45,145,0.15), 0 2px 6px 0 rgba(92,45,145,0.07)",
        nav:          "0 1px 0 0 rgba(92,45,145,0.08)",
      },
      spacing: {
        section: "clamp(3rem, 6vw, 6rem)",
      },
    },
  },
  plugins: [],
};

export default config;
