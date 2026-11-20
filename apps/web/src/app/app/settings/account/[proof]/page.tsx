import { notFound } from "next/navigation";
import Link from "next/link";
import { readPrivate } from "@/lib/workspace-access";
import { EmailProof } from "@/components/account/email-proof";
import styles from "../settings.module.css";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Confirm email change · ResolveFlow AI",
  robots: { index: false, follow: false },
  referrer: "no-referrer" as const,
};

export default async function Page({ params }: { params: Promise<{ proof: string }> }) {
  const { proof } = await params;
  if (proof !== "approve-email" && proof !== "confirm-email") notFound();
  if (!await readPrivate("/account/profile")) {
    return <main className="service-unavailable"><h1>Settings are temporarily unavailable.</h1>
      <Link href="/app/settings/account">Return to settings</Link>
    </main>;
  }
  return <main id="main-content" className={styles.settings}>
    <EmailProof action={proof === "approve-email" ? "approve" : "confirm"} />
  </main>;
}
