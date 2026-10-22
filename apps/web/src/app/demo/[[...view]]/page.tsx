import { notFound } from "next/navigation";
import { DemoApp } from "@/components/demo/demo-app";
export const metadata = { title: "Interactive demo · ResolveFlow AI", description: "Explore synthetic support tickets, evidence-grounded workflow examples and workspace analytics." };
export default async function DemoPage({ params }: { params: Promise<{ view?: string[] }> }) {
  const { view = [] } = await params;
  const section = view[0] ?? "overview";
  if (!["overview", "tickets", "knowledge", "workflows", "analytics", "architecture"].includes(section) || view.length > 2 || (view.length === 2 && !["tickets", "knowledge", "workflows"].includes(section))) notFound();
  return <DemoApp section={section} selected={view[1]} />;
}
