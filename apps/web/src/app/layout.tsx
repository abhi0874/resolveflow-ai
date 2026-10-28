import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: "ResolveFlow AI — Thoughtful support, intelligent foundations",
  description:
    "An AI-powered customer support operations platform combining machine learning, knowledge retrieval, and intelligent workflow orchestration. Currently in development.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>{/* Synchronous local script prevents a saved-theme flash before first paint. */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/theme-init.js" />
      </head>
      <body>{children}</body>
    </html>
  );
}
