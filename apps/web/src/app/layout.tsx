import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResolveFlow AI — Thoughtful support, intelligent foundations",
  description:
    "An AI-powered customer support operations platform combining machine learning, knowledge retrieval, and intelligent workflow orchestration. Currently in development.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
