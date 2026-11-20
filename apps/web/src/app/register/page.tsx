import { appMode } from "@/lib/app-mode";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { accountDestination } from "@/lib/account-navigation";
export const metadata = { title: "Create account · ResolveFlow AI" };
export default async function Register({ searchParams }: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  if (appMode() === "demo") redirect("/demo");
  const destination = accountDestination((await searchParams).next);
  return (
    <AuthLayout register>
      <AuthForm register destination={destination} />
    </AuthLayout>
  );
}
