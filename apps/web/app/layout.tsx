import type { Metadata } from "next";
import "./globals.css";
import { inter, jetbrainsMono } from "./fonts";
import { HostedModeBanner } from "@/components/HostedModeBanner";

export const metadata: Metadata = {
  title: "HackSim, run your own hackathon with agents",
  description:
    "Type one prompt. Autonomous agents on a Gensyn AXL mesh design the bounties, form teams, write real code, score submissions, and crown the winners.",
  metadataBase: new URL("http://localhost:3000"),
  openGraph: {
    title: "HackSim",
    description: "Run your own hackathon with agents.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-surface text-ink antialiased">
        <HostedModeBanner />
        {children}
      </body>
    </html>
  );
}
