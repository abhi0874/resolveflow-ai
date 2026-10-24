import { redirect } from "next/navigation";
import { appMode } from "@/lib/app-mode";
import { AuthLayout } from "@/components/auth/auth-layout";
import { IdentityForm } from "@/components/auth/identity-form";
export const metadata = { title: "Account recovery · ResolveFlow AI", robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default function Page() {
  if (appMode() === "demo") redirect("/demo");
  return <AuthLayout><IdentityForm mode="forgot" /></AuthLayout>;
}
