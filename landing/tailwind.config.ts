import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#FF6B35",
        surface: "#FFFBF7",
        accent: "#22C55E",
        brand: {
          orange: "#FF6B35",
          "orange-dark": "#E55A25",
          "orange-light": "#FFF0EA",
          green: "#22C55E",
          "green-light": "#F0FDF4",
          surface: "#FFFBF7",
          text: "#1A1A1A",
          muted: "#6B7280",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        display: ["var(--font-syne)", "Syne", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 2px 12px 0 rgba(0,0,0,0.07), 0 1px 3px 0 rgba(0,0,0,0.05)",
        "card-hover": "0 8px 24px 0 rgba(0,0,0,0.10), 0 2px 6px 0 rgba(0,0,0,0.06)",
        nav: "0 1px 0 0 rgba(0,0,0,0.06)",
      },
      spacing: {
        "section": "clamp(3rem, 6vw, 6rem)",
      },
    },
  },
  plugins: [],
};

export default config;
