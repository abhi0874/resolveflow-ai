"use client";
import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { api, ApiError, errorMessage } from "@/lib/session-api";

type SearchResponse = {
  query: string;
  min_similarity: number;
  results: {
    document_id: string;
    chunk_id: string;
    document_name: string;
    content: string;
    chunk_index: number;
    page_number: number | null;
    similarity_score: number;
  }[];
};
export function retrievalError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503) return "Local search is unavailable or busy. Try again shortly; the embedding model must be installed on the server.";
    if (error.status === 422) return "Use a nonempty question of up to 1,000 characters. Indexing also requires a document within the configured chunk limit.";
    if (error.status === 409) return "This document is busy or not ready for indexing. Refresh its status and try again.";
    if (error.status === 404) return "This document or workspace is no longer available to you.";
  }
  return errorMessage(error);
}
export function SemanticSearch({ workspaceId }: { workspaceId: string }) {
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    const data = new FormData(event.currentTarget);
    const query = String(data.get("query") ?? "").trim();
    if (!query) { setError("Enter a question to search your knowledge base."); return; }
    busy.current = true;
    setPending(true); setError(""); setResult(null);
    try {
      setResult(await api<SearchResponse>(`/workspaces/${workspaceId}/knowledge-base/search`, "POST", {
        query, top_k: Number(data.get("top_k")),
      }));
    } catch (e) { setError(retrievalError(e)); }
    finally { setPending(false); busy.current = false; }
  }
  return <section className="workspace-card semantic-search" aria-labelledby="semantic-title" aria-busy={pending}>
    <span className="eyebrow">FIND THE RIGHT PASSAGE</span>
    <h2 id="semantic-title">Search by meaning.</h2>
    <p className="field-help">Ask in your own words. Search returns passages from indexed documents in this workspace.</p>
    <form onSubmit={search}>
      <div className="semantic-search-controls">
        <div className="form-field"><label htmlFor="semantic-query">Search knowledge</label>
          <input id="semantic-query" name="query" required maxLength={1000} placeholder="How can a customer get their money back?" disabled={pending} />
        </div>
        <div className="form-field"><label htmlFor="semantic-count">Results</label><select id="semantic-count" name="top_k" defaultValue="5" disabled={pending}>
          <option value="3">3 passages</option><option value="5">5 passages</option><option value="10">10 passages</option>
        </select></div>
        <button className="action-button" disabled={pending}>{pending ? "Searching…" : "Search knowledge"}</button>
      </div>
    </form>
    {pending && <p role="status">Finding related passages in your workspace…</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <div aria-live="polite">
      <p className="field-help">{result.results.length} passages for “{result.query}” · Similarity measures related meaning, not factual correctness.</p>
      {result.results.length === 0 ? <div className="ticket-empty"><h3>No relevant passages found.</h3><p>Try different wording, or open a document and index it for search.</p></div> :
        <ol className="semantic-results">{result.results.map((r) => <li key={r.chunk_id}>
          <div className="chunk-heading"><Link href={`/app/knowledge-base/${r.document_id}?workspace=${workspaceId}`}>{r.document_name}</Link>
            <span className="role-badge">{r.similarity_score.toFixed(3)} similarity</span></div>
          <p className="retrieved-passage">{r.content}</p>
          <small>{r.page_number !== null ? `Page ${r.page_number} · ` : "Text source · "}Chunk {r.chunk_index + 1}</small>
          <Link className="back-link" href={`/app/knowledge-base/${r.document_id}?workspace=${workspaceId}`}>View source document →</Link>
        </li>)}</ol>}
    </div>}
  </section>;
}
