import type { Config } from "tailwindcss";

// Design tokens lifted from refs/PLAN.md section 6 and refs/UX_SPEC.md.
// These are the only colour and font tokens the app uses. Any new token must
// be added here first, named, and reviewed before it appears in component code.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#000000",
        body: "#374151",
        muted: "#6B7280",
        surface: "#FFFFFF",
        canvas: "#F9FAFB",
        border: "#D1D5DB",
        navy: { DEFAULT: "#21294C", 950: "#2F2B43" },
        accent: { DEFAULT: "#8347FF", soft: "#F3E8FF" },
        success: { DEFAULT: "#22C55E", soft: "#DCFCE7", ink: "#166534" },
        warning: { DEFAULT: "#F59E0B", soft: "#FEF3C7" },
        coral: "#FF8585",
        gold: "#FFC857",
        silver: "#C0C0C0",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-general-sans)", "var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        "3xl": "1.5rem",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgb(0 0 0 / 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
