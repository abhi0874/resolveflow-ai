"use client";

import { useEffect, useState } from "react";
import { checkApiHealth } from "@/lib/api";

type ConnectionState = "checking" | "connected" | "unavailable";

const labels: Record<ConnectionState, string> = {
  checking: "Checking API connection…",
  connected: "API connected",
  unavailable: "API unavailable",
};

export function ApiStatus() {
  const [status, setStatus] = useState<ConnectionState>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 4000);
    checkApiHealth(controller.signal)
      .then(() => {
        if (active) setStatus("connected");
      })
      .catch(() => {
        if (active) setStatus("unavailable");
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [attempt]);

  return (
    <div className="api-status">
      <div>
        <span className="eyebrow">DEVELOPMENT CONNECTION</span>
        <p role="status" className={`connection-label connection-${status}`}>
          <span className="small-dot" aria-hidden="true" />
          {labels[status]}
        </p>
        <p className="connection-help">
          {status === "unavailable"
            ? "The page still works. Start the local API, then check again."
            : "A live check of the local health endpoint. No AI services connected."}
        </p>
      </div>
      <button
        type="button"
        className="check-button"
        disabled={status === "checking"}
        onClick={() => {
          setStatus("checking");
          setAttempt((value) => value + 1);
        }}
      >
        {status === "checking" ? "Checking…" : "Check again"}
      </button>
    </div>
  );
}
