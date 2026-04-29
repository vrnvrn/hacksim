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

// General Sans, the display font, served from Fontshare.
//
// The brief asks for next/font/local pointing at a woff2 we ship under
// public/fonts/. The ITF file ships under the Fontshare Free License and is
// not redistributable through this repo without the user downloading it
// explicitly. To keep the build green out of the box we wire the local file
// through CSS @font-face inside globals.css and gracefully fall back to
// Inter when the file is absent. Drop public/fonts/GeneralSans-Variable.woff2
// in place to activate it. See apps/web/public/fonts/README.txt for the
// source URL and licence.
