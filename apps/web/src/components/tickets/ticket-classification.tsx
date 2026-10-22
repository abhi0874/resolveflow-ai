"use client";
import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/session-api";
import { ticketError, type Ticket } from "@/lib/tickets";

type Classification = {
  ticket_id: string;
  ticket_version: number;
  predicted_category: string;
  suggested_category: string | null;
  score: number;
  score_kind: "uncalibrated_model_probability";
  threshold: number;
  uncertain: boolean;
  human_review_recommended: boolean;
  model_version: string;
};

export function TicketClassification({ base, ticket, onAccepted }: {
  base: string;
  ticket: Ticket;
  onAccepted: (ticket: Ticket) => void;
}) {
  const [result, setResult] = useState<Classification | null>(null);
  const [pending, setPending] = useState<"classify" | "accept" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const busy = useRef(false);
  async function classify() {
    if (busy.current) return;
    busy.current = true;
    setPending("classify"); setError(""); setNotice(""); setResult(null);
    try {
      const prediction = await api<Classification>(base + "/classify", "POST", {});
      if (prediction.ticket_id !== ticket.id || prediction.ticket_version !== ticket.version) {
        setError("This ticket changed. Refresh it before classifying again.");
      } else setResult(prediction);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 503
        ? "The ML classifier is unavailable. You can still edit the category manually."
        : ticketError(e));
    } finally { busy.current = false; setPending(null); }
  }
  async function accept() {
    if (!result?.suggested_category || busy.current) return;
    busy.current = true; setPending("accept"); setError("");
    try {
      const updated = await api<Ticket>(base, "PATCH", {
        category: result.suggested_category,
        expected_version: result.ticket_version,
      });
      setResult(null);
      onAccepted(updated);
    } catch (e) { setError(ticketError(e)); }
    finally { busy.current = false; setPending(null); }
  }
  return <section className="workspace-card classification-card" aria-label="ML classification" aria-busy={pending !== null}>
    <div className="card-heading">
      <div><span className="eyebrow">LOCAL MACHINE LEARNING</span><h2>Ticket classification</h2></div>
      <button className="action-button" disabled={pending !== null} onClick={() => void classify()}>
        {pending === "classify" ? "Classifying…" : "Classify with ML"}
      </button>
    </div>
    <p className="field-help">A trained text classifier suggests a category. Review it before applying; your ticket stays unchanged until you accept.</p>
    {pending === "classify" && <p role="status">Classifying this ticket…</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status" className="success-message">{notice}</p>}
    {result && <div className="classification-result">
      <span className="role-badge">{result.uncertain ? "Uncertain · manual review needed" : "Suggestion · review before applying"}</span>
      <h3>{result.uncertain ? "No reliable suggestion" : result.suggested_category}</h3>
      {result.uncertain && <p>Highest-scoring category: {result.predicted_category}. The model has insufficient evidence to offer it as a suggestion. You can choose a category in Edit ticket.</p>}
      <dl className="classification-metadata">
        <div><dt>Model score</dt><dd>{(result.score * 100).toFixed(1)}%</dd></div>
        <div><dt>Suggestion threshold</dt><dd>{(result.threshold * 100).toFixed(0)}%</dd></div>
        <div><dt>Model version</dt><dd>{result.model_version}</dd></div>
      </dl>
      <p className="field-help">Uncalibrated model probability, not a measured chance of correctness. Trained on synthetic English examples; this is not an LLM response.</p>
      <div className="ticket-actions">
        {result.suggested_category && <button className="action-button" disabled={pending !== null} onClick={() => void accept()}>{pending === "accept" ? "Applying…" : "Accept suggestion"}</button>}
        <button className="subtle-button" disabled={pending !== null} onClick={() => { setResult(null); setError(""); setNotice("Suggestion dismissed. Ticket category unchanged."); }}>Dismiss suggestion</button>
      </div>
    </div>}
  </section>;
}
