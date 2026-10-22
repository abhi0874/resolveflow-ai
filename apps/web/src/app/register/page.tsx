import { appMode } from "@/lib/app-mode";
import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
export const metadata = { title: "Create account · ResolveFlow AI" };
export default function Register() {
  if (appMode() === "demo") redirect("/demo");
  return (
    <AuthLayout register>
      <AuthForm register />
    </AuthLayout>
  );
}
