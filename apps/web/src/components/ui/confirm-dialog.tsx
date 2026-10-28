"use client";

import { useEffect, useId, useRef } from "react";

/** Native modal semantics keep focus inside the dialog and make the page inert. */
export function ConfirmDialog({ title, description, confirmLabel, onConfirm, onCancel }: {
  title: string; description: string; confirmLabel: string;
  onConfirm: () => void; onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = ref.current;
    dialog?.showModal();
    return () => { dialog?.close(); if (opener?.isConnected) opener.focus(); };
  }, []);
  return <dialog ref={ref} className="confirm-dialog" aria-labelledby={`${id}-title`}
    aria-describedby={`${id}-description`} onKeyDown={event => {
      if (event.key !== "Tab") return;
      const buttons = ref.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
      if (!buttons?.length) return;
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }} onCancel={event => { event.preventDefault(); onCancel(); }}>
    <span className="eyebrow">YOUR DEMO WORKSPACE</span>
    <h2 id={`${id}-title`}>{title}</h2>
    <p id={`${id}-description`}>{description}</p>
    <div className="ticket-actions">
      <button className="subtle-button" onClick={onCancel}>Keep exploring</button>
      <button className="action-button" onClick={onConfirm}>{confirmLabel}</button>
    </div>
  </dialog>;
}
