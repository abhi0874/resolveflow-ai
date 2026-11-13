import localFont from "next/font/local";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./design-system.css";

const heading = localFont({ src: "./fonts/SpaceGrotesk-Variable.ttf", variable: "--font-heading", display: "swap", weight: "300 700" });
const body = localFont({ src: "./fonts/Manrope-Variable.ttf", variable: "--font-body", display: "swap", weight: "200 800" });

export const metadata: Metadata = {
  title: "ResolveFlow AI — Support intelligence, with a human perspective",
  description:
    "Explore a synthetic support workspace and the Python, ML, retrieval and human-reviewed workflow engineering behind ResolveFlow AI.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html className={`${heading.variable} ${body.variable}`} lang="en" data-theme="dark" suppressHydrationWarning>
      <head>{/* Synchronous local script prevents a saved-theme flash before first paint. */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/theme-init.js" />
      </head>
      <body>{children}</body>
    </html>
  );
}
