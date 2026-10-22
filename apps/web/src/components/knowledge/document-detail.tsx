"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type Workspace } from "@/lib/session-api";
import { dateLabel, type ResultPage } from "@/lib/tickets";
import {
  documentError,
  downloadDocument,
  fileSize,
  fileType,
  type KnowledgeDocument,
  type DocumentChunk,
} from "@/lib/documents";
import { DocumentIndex } from "./document-index";
import { DocumentBadge } from "./knowledge-list";
export function DocumentDetail({
  workspace,
  documentId,
}: {
  workspace: Workspace;
  documentId: string;
}) {
  const router = useRouter();
  const [doc, setDoc] = useState<KnowledgeDocument | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const busy = useRef(false);
  const base = `/workspaces/${workspace.id}/documents/${encodeURIComponent(documentId)}`;
  useEffect(() => {
    let current = true;
    api<KnowledgeDocument>(base)
      .then((value) => {
        if (current) {
          setDoc(value);
          setError("");
        }
      })
      .catch((e) => {
        if (current) {
          setDoc(null);
          setError(documentError(e));
        }
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [base, revision]);
  async function perform(action: () => Promise<void>) {
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(documentError(e));
    } finally {
      busy.current = false;
      setPending(false);
    }
  }
  const content = workspace.permissions.includes("document:content");
  const remove = workspace.permissions.includes("document:delete");
  const retry = workspace.permissions.includes("document:upload");
  return (
    <>
      <Link
        className="back-link"
        href={`/app/knowledge-base?workspace=${workspace.id}`}
      >
        ← Knowledge base
      </Link>
      {loading ? (
        <div role="status" aria-label="Loading document">
          {[1, 2, 3].map((i) => (
            <div key={i} className="ticket-skeleton" />
          ))}
        </div>
      ) : (
        doc && (
          <>
            <header className="workspace-heading ticket-detail-heading">
              <div>
                <span className="eyebrow">
                  DOCUMENT / {fileType(doc.content_type)}
                </span>
                <h1>{doc.original_filename}</h1>
                <DocumentBadge status={doc.processing_status} />
              </div>
              <div className="ticket-actions">
                {content && doc.processing_status === "completed" && (
                  <button
                    className="action-button"
                    disabled={pending}
                    onClick={() =>
                      void perform(() =>
                        downloadDocument(base, doc.original_filename),
                      )
                    }
                  >
                    Download original ↓
                  </button>
                )}
                <button
                  className="subtle-button"
                  disabled={pending}
                  onClick={() => {
                    setLoading(true);
                    setRevision((v) => v + 1);
                  }}
                >
                  Refresh status
                </button>
              </div>
            </header>
            {doc.processing_error && (
              <div className="document-processing-error" role="status">
                <strong>
                  {doc.processing_status === "deleting"
                    ? "Deletion needs attention"
                    : "Processing needs attention"}
                </strong>
                <p>{doc.processing_error}</p>
                {retry && doc.processing_status === "failed" && (
                  <button
                    className="subtle-button"
                    disabled={pending}
                    onClick={() =>
                      void perform(async () => {
                        setDoc(
                          await api<KnowledgeDocument>(base + "/retry", "POST"),
                        );
                        setRevision((v) => v + 1);
                      })
                    }
                  >
                    {pending ? "Processing…" : "Retry processing"}
                  </button>
                )}
              </div>
            )}
            {["pending", "processing"].includes(doc.processing_status) && (
              <p role="status" className="field-help">
                This document is not ready yet. Refresh to check its processing
                status.
              </p>
            )}
            <DocumentIndex doc={doc} base={base} allowed={retry} onUpdate={setDoc} />
            <div className="document-detail-grid">
              <section className="workspace-card document-preview">
                <span className="eyebrow">EXTRACTED CONTENT</span>
                <h2>Document chunks</h2>
                <p className="field-help">
                  {doc.total_chunks} chunks · Plain-text preview with source
                  references
                </p>
                {content && doc.processing_status === "completed" ? (
                  <ChunkList key={revision} base={base} />
                ) : (
                  <div className="ticket-empty">
                    <p>
                      {content
                        ? "Extracted chunks will appear after processing completes."
                        : "Your role can view document metadata. Content and downloads require support access."}
                    </p>
                  </div>
                )}
              </section>
              <aside className="workspace-card ticket-properties">
                <span className="eyebrow">SOURCE DETAILS</span>
                <h2>About this file</h2>
                <dl>
                  <dt>File type</dt>
                  <dd>{fileType(doc.content_type)}</dd>
                  <dt>Size</dt>
                  <dd>{fileSize(doc.file_size)}</dd>
                  <dt>Uploaded by</dt>
                  <dd>{doc.uploaded_by_email}</dd>
                  <dt>Uploaded</dt>
                  <dd>
                    <time dateTime={doc.created_at}>
                      {dateLabel(doc.created_at)}
                    </time>
                  </dd>
                  <dt>Last updated</dt>
                  <dd>
                    <time dateTime={doc.updated_at}>
                      {dateLabel(doc.updated_at)}
                    </time>
                  </dd>
                  <dt>Extracted chunks</dt>
                  <dd>{doc.total_chunks}</dd>
                </dl>
                {remove && (
                  <div className="document-delete">
                    <p className="field-help">
                      Deletion removes the file and its extracted chunks from
                      this workspace.
                    </p>
                    <button
                      className="subtle-button danger-button"
                      disabled={pending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Delete "${doc.original_filename}" and all its extracted chunks? This cannot be undone.`,
                          )
                        )
                          void perform(async () => {
                            await api(base, "DELETE");
                            router.push(
                              `/app/knowledge-base?workspace=${workspace.id}`,
                            );
                          });
                      }}
                    >
                      {doc.processing_status === "deleting"
                        ? "Retry deletion"
                        : "Delete document"}
                    </button>
                  </div>
                )}
              </aside>
            </div>
          </>
        )
      )}
      {error && (
        <div className="workspace-card">
          <p className="form-error" role="alert">
            {error}
          </p>
          <button
            className="subtle-button"
            disabled={pending}
            onClick={() => {
              setLoading(true);
              setRevision((v) => v + 1);
            }}
          >
            Try again
          </button>
        </div>
      )}
    </>
  );
}
function ChunkList({ base }: { base: string }) {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<ResultPage<DocumentChunk> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let current = true;
    api<ResultPage<DocumentChunk>>(`${base}/chunks?page=${page}&page_size=5`)
      .then((value) => {
        if (current) {
          setResult(value);
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
  }, [base, page, revision]);
  return (
    <div aria-busy={loading}>
      {error ? (
        <>
          <p className="form-error" role="alert">
            {error}
          </p>
          <button
            className="subtle-button"
            onClick={() => {
              setLoading(true);
              setRevision((v) => v + 1);
            }}
          >
            Retry preview
          </button>
        </>
      ) : loading ? (
        <p role="status">Loading chunks…</p>
      ) : (
        <>
          <ol className="document-chunks" aria-label="Document chunks">
            {result?.items.map((chunk) => (
              <li key={chunk.id}>
                <div className="chunk-heading">
                  <span>Chunk {chunk.chunk_index + 1}</span>
                  <span>
                    {chunk.page_number
                      ? `Page ${chunk.page_number}`
                      : "Text source"}{" "}
                    · {chunk.character_count} characters
                  </span>
                </div>
                <pre>{chunk.content}</pre>
                <small>
                  {chunk.source_metadata.filename} · Characters{" "}
                  {chunk.source_metadata.start_offset}–
                  {chunk.source_metadata.end_offset}
                </small>
              </li>
            ))}
          </ol>
          {result && result.pages > 1 && (
            <div className="ticket-pagination">
              <span>
                Page {result.page} of {result.pages}
              </span>
              <button
                className="subtle-button"
                disabled={page <= 1}
                onClick={() => {
                  setLoading(true);
                  setPage((v) => v - 1);
                }}
              >
                Previous chunks
              </button>
              <button
                className="subtle-button"
                disabled={page >= result.pages}
                onClick={() => {
                  setLoading(true);
                  setPage((v) => v + 1);
                }}
              >
                Next chunks
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
