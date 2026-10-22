import { TicketPage } from "@/components/tickets/ticket-page";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Ticket details · ResolveFlow AI",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
  params,
}: {
  searchParams: Promise<{ workspace?: string }>;
  params: Promise<{ ticketId: string }>;
}) {
  return (
    <TicketPage
      workspaceId={(await searchParams).workspace}
      ticketId={(await params).ticketId}
    />
  );
}
