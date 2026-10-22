"use client";
import { useRef, useState } from "react";
import { api } from "@/lib/session-api";
import type { KnowledgeDocument } from "@/lib/documents";
import { retrievalError } from "./semantic-search";
export const indexingLabels = { not_indexed: "Not indexed", indexing: "Indexing", indexed: "Indexed", failed: "Indexing failed" } as const;
export function DocumentIndex({ doc, base, allowed, onUpdate }: {
  doc: KnowledgeDocument; base: string; allowed: boolean; onUpdate: (value: KnowledgeDocument) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const busy = useRef(false);
  async function index() {
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      const updated = await api<KnowledgeDocument>(base + "/index", "POST", { force: doc.indexed_model !== null });
      onUpdate(updated);
      if (updated.indexing_status === "failed") setError("Indexing could not finish. Previously indexed, unchanged passages remain available. Retry when the model is available.");
    } catch (e) { setError(retrievalError(e)); }
    finally { setPending(false); busy.current = false; }
  }
  return <section className="workspace-card document-index" aria-busy={pending}>
    <div><span className="eyebrow">SEMANTIC SEARCH</span><h2>{pending ? "Indexing…" : indexingLabels[doc.indexing_status]}</h2>
      <p className="field-help">Index extracted text to make it searchable by meaning. Indexing runs during this request with bounded batches; it is not a background job.</p>
      {doc.indexed_model && <details><summary>Indexed model</summary><p className="field-help">{doc.indexed_model}</p><p className="field-help">After a model change, reindex to make this document searchable with the active model.</p></details>}
      {doc.indexing_status === "failed" && <p role="status">The last indexing attempt failed. You can retry.</p>}
      {doc.indexing_status === "indexing" && !pending && <p role="status">Refresh to check status. An interrupted attempt can be retried after its recovery window.</p>}
    </div>
    {allowed && doc.processing_status === "completed" && <button className="action-button" disabled={pending} onClick={() => void index()}>{pending ? "Indexing…" : doc.indexed_model ? "Reindex document" : "Index document"}</button>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
