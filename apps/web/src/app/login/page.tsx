import { appMode } from "@/lib/app-mode";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
export const metadata = { title: "Sign in · ResolveFlow AI" };
export default function Login() {
  if (appMode() === "demo") redirect("/demo");
  return (
    <AuthLayout>
      <AuthForm />
    </AuthLayout>
  );
}
