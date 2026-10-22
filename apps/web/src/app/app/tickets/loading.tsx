export default function Loading() {
  return (
    <main
      className="ticket-loading"
      aria-busy="true"
      aria-label="Loading tickets"
    >
      <p>Loading your workspace…</p>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="ticket-skeleton" />
      ))}
    </main>
  );
}
