import { Inter, JetBrains_Mono } from "next/font/google";

// Inter Variable, the body font. Subsetted to latin to keep the bundle small.
export const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

// JetBrains Mono, the run-log and code-tab font.
export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

// The display font is Inter Variable as well. We previously had a CSS
// @font-face block pointing at /fonts/GeneralSans-Variable.woff2; the woff2
// is licence-restricted from Fontshare and never shipped, so the @font-face
// fired one 404 per styled element. To bring General Sans back, drop the
// woff2 into apps/web/public/fonts/ and add the @font-face rule in
// globals.css; then prepend "General Sans" to --font-display.
