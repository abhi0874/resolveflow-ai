import { appMode } from "@/lib/app-mode";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { accountDestination } from "@/lib/account-navigation";
export const metadata = { title: "Sign in · ResolveFlow AI" };
export default async function Login({ searchParams }: {
  searchParams: Promise<{ next?: string | string[]; google?: string; deleted?: string }>;
}) {
  if (appMode() === "demo") redirect("/demo");
  const query = await searchParams;
  const destination = accountDestination(query.next);
  return (
    <AuthLayout>
      {query.deleted === "yes" && <p role="status">Your ResolveFlow account was deleted.</p>}
      {query.deleted === "review" && <p role="status">Your account was deleted. Some private files remain under restricted cleanup or review.</p>}
      <AuthForm googleFailed={query.google === "failed"} destination={destination} />
    </AuthLayout>
  );
}
