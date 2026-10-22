export default function Loading() {
  return (
    <main
      className="ticket-loading"
      aria-busy="true"
      aria-label="Loading knowledge base"
    >
      <p>Loading your knowledge base…</p>
      {[1, 2, 3].map((i) => (
        <div className="ticket-skeleton" key={i} />
      ))}
    </main>
  );
}
