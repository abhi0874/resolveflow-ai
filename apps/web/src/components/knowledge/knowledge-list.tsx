"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api, type Workspace } from "@/lib/session-api";
import { dateLabel, type ResultPage } from "@/lib/tickets";
import {
  documentError,
  documentStatuses,
  fileSize,
  fileType,
  type KnowledgeDocument,
  type UploadConfig,
} from "@/lib/documents";
import { SemanticSearch } from "./semantic-search";
import { indexingLabels } from "./document-index";
import { DocumentUpload } from "./document-upload";
export function KnowledgeList({
  workspace,
  config,
}: {
  workspace: Workspace;
  config: UploadConfig;
}) {
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("page=1&page_size=25");
  const [result, setResult] = useState<ResultPage<KnowledgeDocument> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const base = `/workspaces/${workspace.id}/documents`;
  useEffect(() => {
    let current = true;
    api<ResultPage<KnowledgeDocument>>(`${base}?${query}`)
      .then((data) => {
        if (current) {
          setResult(data);
          setError("");
        }
      })
      .catch((e) => {
        if (current) setError(documentError(e));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [base, query, revision]);
  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams({ page: "1", page_size: "25" });
    for (const [k, v] of new FormData(event.currentTarget))
      if (String(v).trim()) params.set(k, String(v).trim());
    setLoading(true);
    setQuery(params.toString());
    setRevision((v) => v + 1);
  }
  function changePage(page: number) {
    const params = new URLSearchParams(query);
    params.set("page", String(page));
    setLoading(true);
    setQuery(params.toString());
  }
  const write = workspace.permissions.includes("document:upload");
  return (
    <>
      <header className="workspace-heading">
        <div>
          <span className="eyebrow">{workspace.name} / SHARED KNOWLEDGE</span>
          <h1>Knowledge base.</h1>
          <p>
            The context your team can count on. Keep your guides and reference
            documents together.
          </p>
        </div>
        {write && !uploading && (
          <button className="action-button" onClick={() => setUploading(true)}>
            ↑ Upload document
          </button>
        )}
      </header>
      {uploading ? (
        <DocumentUpload
          workspaceId={workspace.id}
          config={config}
          onCancel={() => setUploading(false)}
        />
      ) : (
        <>
          {workspace.permissions.includes("document:content") && <SemanticSearch workspaceId={workspace.id} />}
          <section className="knowledge-banner">
            <div className="document-file-icon" aria-hidden="true">
              ▤
            </div>
            <div>
              <h2>A shared source of context.</h2>
              <p>
                Upload documents, inspect extracted text, and keep your team’s
                reference material organized.
              </p>
            </div>
            <span className="role-badge">Private workspace library</span>
          </section>
          <section className="ticket-toolbar" aria-label="Document filters">
            <form onSubmit={filter}>
              <div className="ticket-search-row">
                <div className="form-field">
                  <label htmlFor="document-search">Search documents</label>
                  <input
                    id="document-search"
                    name="search"
                    maxLength={200}
                    placeholder="Search by filename…"
                  />
                </div>
                <button className="action-button">Apply filters</button>
              </div>
              <div className="ticket-filters">
                <div className="form-field">
                  <label htmlFor="document-status">Processing status</label>
                  <select id="document-status" name="status">
                    <option value="">All statuses</option>
                    {Object.entries(documentStatuses).map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="document-sort">Sort by</label>
                  <select id="document-sort" name="sort">
                    <option value="created_at">Upload date</option>
                    <option value="file_size">File size</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="document-direction">Order</label>
                  <select id="document-direction" name="direction">
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </div>
              </div>
              <button
                type="reset"
                className="subtle-button"
                onClick={() => {
                  setLoading(true);
                  setQuery("page=1&page_size=25");
                  setRevision((v) => v + 1);
                }}
              >
                Clear filters
              </button>
            </form>
          </section>
          <section
            className="workspace-card ticket-list"
            aria-label="Document results"
            aria-busy={loading}
          >
            <div className="card-heading">
              <h2>Your documents</h2>
              <span className="role-badge">
                {loading ? "Loading…" : `${result?.total ?? 0} ${result?.total === 1 ? "document" : "documents"}`}
              </span>
            </div>
            {error ? (
              <div className="ticket-empty">
                <p role="alert" className="form-error">
                  {error}
                </p>
                <button
                  className="subtle-button"
                  onClick={() => {
                    setLoading(true);
                    setRevision((v) => v + 1);
                  }}
                >
                  Try again
                </button>
              </div>
            ) : loading ? (
              <div role="status" aria-label="Loading documents">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="ticket-skeleton" />
                ))}
              </div>
            ) : result?.items.length ? (
              <>
                <div className="ticket-table-scroll">
                  <table className="ticket-table">
                    <caption className="sr-only">
                      Documents in {workspace.name}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Document</th>
                        <th scope="col">Status</th>
                        <th scope="col">Size</th>
                        <th scope="col">Chunks</th>
                        <th scope="col">Uploaded</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.items.map((doc) => (
                        <tr key={doc.id}>
                          <td>
                            <div className="document-cell">
                              <span className="document-file-icon">
                                {fileType(doc.content_type)}
                              </span>
                              <div>
                                <Link
                                  className="ticket-title-link"
                                  href={`/app/knowledge-base/${doc.id}?workspace=${workspace.id}`}
                                >
                                  {doc.original_filename}
                                </Link>
                                <small>{doc.uploaded_by_email}</small>
                              </div>
                            </div>
                          </td>
                          <td>
                            <DocumentBadge status={doc.processing_status} /><small>{indexingLabels[doc.indexing_status]}</small>
                          </td>
                          <td>{fileSize(doc.file_size)}</td>
                          <td>{doc.total_chunks}</td>
                          <td>
                            <time dateTime={doc.created_at}>
                              {dateLabel(doc.created_at)}
                            </time>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="ticket-pagination">
                  <span>
                    Page {result.page} of {result.pages}
                  </span>
                  <div>
                    <button
                      className="subtle-button"
                      disabled={result.page <= 1}
                      onClick={() => changePage(result.page - 1)}
                    >
                      ← Previous
                    </button>
                    <button
                      className="subtle-button"
                      disabled={result.page >= result.pages}
                      onClick={() => changePage(result.page + 1)}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="ticket-empty">
                <span className="empty-symbol" aria-hidden="true">
                  ▤
                </span>
                <h3>No documents found.</h3>
                <p>
                  {write
                    ? "Add your first guide, or clear the filters to see your library."
                    : "Your workspace’s documents will appear here. Ask a support teammate to upload a guide."}
                </p>
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
export function DocumentBadge({
  status,
}: {
  status: KnowledgeDocument["processing_status"];
}) {
  return (
    <span className={`ticket-badge document-badge-${status}`}>
      ● {documentStatuses[status]}
    </span>
  );
}
