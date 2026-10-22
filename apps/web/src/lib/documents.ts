import { ApiError, errorMessage } from "./session-api";
export const documentStatuses = {
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
  deleting: "Deleting",
} as const;
export type KnowledgeDocument = {
  id: string;
  workspace_id: string;
  uploaded_by: string;
  uploaded_by_email: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  checksum: string;
  processing_status: keyof typeof documentStatuses;
  total_chunks: number;
  processing_error: string | null;
  indexing_status: "not_indexed" | "indexing" | "indexed" | "failed";
  indexing_error: string | null;
  indexed_model: string | null;
  created_at: string;
  updated_at: string;
};
export type DocumentChunk = {
  id: string;
  document_id: string;
  workspace_id: string;
  chunk_index: number;
  content: string;
  character_count: number;
  page_number: number | null;
  source_metadata: {
    filename: string;
    start_offset: number;
    end_offset: number;
    pipeline_version: number;
  };
};
export type UploadConfig = {
  max_bytes: number;
  formats: string[];
  max_pages: number;
  chunk_size: number;
  chunk_overlap: number;
};
export function fileSize(bytes: number) {
  return bytes >= 1048576
    ? `${(bytes / 1048576).toFixed(1)} MB`
    : `${Math.max(1, Math.ceil(bytes / 1024))} KB`;
}
export function fileType(mime: string) {
  return mime === "application/pdf"
    ? "PDF"
    : mime === "text/markdown"
      ? "MD"
      : "TXT";
}
export function documentError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404)
      return "This document or workspace is unavailable, or your access has changed.";
    if (error.status === 409)
      return "This document is busy or its content is not ready. Refresh its status and try again.";
    if (error.status === 413)
      return "This file exceeds the upload limit. Choose a smaller file.";
    if (error.status === 415) return "Choose a PDF, TXT or Markdown document.";
    if (error.status === 422)
      return "The file or request is invalid. Check its name, format and text encoding.";
  }
  return errorMessage(error);
}
export async function uploadDocument(
  base: string,
  file: File,
  onProgress: (value: number | null) => void,
): Promise<KnowledgeDocument> {
  const csrf = await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin",
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!csrf.ok) throw new ApiError(csrf.status);
  const token = (await csrf.json()).csrf_token;
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/v1" + base);
    xhr.timeout = 60000;
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.setRequestHeader("X-CSRF-Token", token);
    xhr.setRequestHeader("X-Upload-Filename", encodeURIComponent(file.name));
    xhr.upload.onprogress = (event) =>
      onProgress(
        event.lengthComputable
          ? Math.round((event.loaded / event.total) * 100)
          : null,
      );
    xhr.onerror = () => reject(new Error("Network error"));
    xhr.ontimeout = () => reject(new Error("Upload timed out"));
    xhr.onabort = () => reject(new Error("Upload cancelled"));
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiError(xhr.status));
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText));
      } catch {
        reject(new Error("Invalid response"));
      }
    };
    xhr.send(file);
  });
}
export async function downloadDocument(base: string, filename: string) {
  const response = await fetch("/api/v1" + base + "/download", {
    credentials: "same-origin",
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new ApiError(response.status);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
