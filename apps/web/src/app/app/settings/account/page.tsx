import Link from "next/link";
import { AccountSettings, type AccountProfile } from "@/components/account/account-settings";
import { readPrivate } from "@/lib/workspace-access";
import styles from "./settings.module.css";

export const dynamic = "force-dynamic";
export const metadata = {
  title: "Personal settings · ResolveFlow AI",
  robots: { index: false, follow: false },
};

export default async function Page() {
  const profile = await readPrivate("/account/profile");
  if (!profile) {
    return <main className="service-unavailable"><h1>Settings are temporarily unavailable.</h1>
      <Link className="primary-link" href="/app/settings/account">Try again</Link>
    </main>;
  }
  const account: AccountProfile = await profile.json();
  return <main id="main-content" className={styles.settings}>
    <header>
      <Link href="/app" className="subtle-button">← Back to workspaces</Link>
      <h1>Personal settings</h1>
    </header>
    <AccountSettings profile={account} />
  </main>;
}
