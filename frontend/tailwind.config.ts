import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0e1a",
        surface: "#111827",
        "surface-2": "#1f2937",
        "surface-3": "#374151",
        border: "#1f2937",
        "border-subtle": "#374151",
        primary: "#6366f1",
        "primary-hover": "#818cf8",
        "primary-muted": "#312e81",
        success: "#10b981",
        "success-muted": "#064e3b",
        warning: "#f59e0b",
        "warning-muted": "#451a03",
        danger: "#ef4444",
        "danger-muted": "#450a0a",
        muted: "#6b7280",
        subtle: "#4b5563",
        // EV colors
        "ev-elite": "#00ff87",
        "ev-strong": "#22d3ee",
        "ev-good": "#60a5fa",
        "ev-slight": "#a78bfa",
        "ev-negative": "#f87171",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-in": "slideIn 0.2s ease-out",
        "fade-in": "fadeIn 0.3s ease-out",
      },
      keyframes: {
        slideIn: {
          "0%": { transform: "translateY(-10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
