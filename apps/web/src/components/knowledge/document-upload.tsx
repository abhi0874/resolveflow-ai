"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  documentError,
  fileSize,
  uploadDocument,
  type UploadConfig,
} from "@/lib/documents";
export function DocumentUpload({
  workspaceId,
  config,
  onCancel,
}: {
  workspaceId: string;
  config: UploadConfig;
  onCancel: () => void;
}) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const busy = useRef(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  function choose(files: FileList | null) {
    if (busy.current) return;
    setError("");
    setFile(null);
    if (!files?.length) return;
    if (files.length !== 1) {
      setError("Choose one document at a time.");
      return;
    }
    const selected = files[0];
    const extension = selected.name.split(".").at(-1)?.toLowerCase();
    if (!extension || !config.formats.includes(extension)) {
      setError("Choose a PDF, TXT or Markdown document.");
      return;
    }
    if (!selected.size) {
      setError("This file is empty. Choose a document with text.");
      return;
    }
    if (selected.size > config.max_bytes) {
      setError(`Choose a file no larger than ${fileSize(config.max_bytes)}.`);
      return;
    }
    setFile(selected);
  }
  async function submit() {
    if (!file || busy.current) return;
    busy.current = true;
    setPending(true);
    setError("");
    setProgress(null);
    try {
      const document = await uploadDocument(
        `/workspaces/${workspaceId}/documents`,
        file,
        setProgress,
      );
      router.push(
        `/app/knowledge-base/${document.id}?workspace=${workspaceId}`,
      );
    } catch (e) {
      setError(documentError(e));
      busy.current = false;
      setPending(false);
    }
  }
  return (
    <section
      className="workspace-card document-upload"
      aria-label="Document upload"
      aria-busy={pending}
    >
      <span className="eyebrow">ADD TO YOUR LIBRARY</span>
      <h2>Upload a document</h2>
      <p className="field-help">
        PDF, TXT or Markdown · Up to {fileSize(config.max_bytes)} · Text PDFs up
        to {config.max_pages} pages
      </p>
      <div
        className={`document-dropzone ${dragging ? "is-dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!pending) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          choose(event.dataTransfer.files);
        }}
      >
        <span aria-hidden="true" className="document-upload-icon">
          ↑
        </span>
        <h3>{file ? file.name : "Drop your document here"}</h3>
        <p>
          {file ? fileSize(file.size) : "or choose a file from your computer"}
        </p>
        <input
          ref={input}
          type="file"
          accept=".pdf,.txt,.md"
          aria-label="Choose document file"
          className="sr-only"
          disabled={pending}
          onChange={(event) => choose(event.target.files)}
        />
        <button
          className="subtle-button"
          type="button"
          disabled={pending}
          onClick={() => input.current?.click()}
        >
          {file ? "Choose another file" : "Choose file"}
        </button>
      </div>
      <p className="field-help">
        Documents stay private to this workspace. Scanned PDFs need OCR, which
        is not available yet. Markdown is previewed as plain text.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {pending && (
        <div className="document-progress" role="status">
          <p>
            {progress === 100
              ? "Upload sent. Extracting text and preparing chunks…"
              : progress === null
                ? "Uploading document…"
                : `Sending file… ${progress}%`}
          </p>
          {progress !== null && progress < 100 && (
            <progress
              value={progress}
              max={100}
              aria-label="File transfer progress"
            />
          )}
        </div>
      )}
      <div className="ticket-actions">
        <button
          className="action-button"
          disabled={pending || !file}
          onClick={() => void submit()}
        >
          {pending ? "Processing…" : "Upload document"}
        </button>
        <button className="subtle-button" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </section>
  );
}
