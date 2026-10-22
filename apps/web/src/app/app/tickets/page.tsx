import { TicketPage } from "@/components/tickets/ticket-page";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Tickets · ResolveFlow AI",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ workspace?: string }>;
}) {
  return <TicketPage workspaceId={(await searchParams).workspace} />;
}
