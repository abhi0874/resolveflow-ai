"use client";

import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";
function snapshot(): Theme { return document.documentElement.dataset.theme === "light" ? "light" : "dark"; }
function subscribe(update: () => void) {
  function storage(event: StorageEvent) {
    if (event.key !== "resolveflow-theme" && event.key !== null) return;
    document.documentElement.dataset.theme = event.newValue === "light" ? "light" : "dark";
    update();
  }
  window.addEventListener("resolveflow-theme", update);
  window.addEventListener("storage", storage);
  return () => { window.removeEventListener("resolveflow-theme", update); window.removeEventListener("storage", storage); };
}
const serverSnapshot = (): Theme => "dark";
function select(value: Theme) {
    document.documentElement.dataset.theme = value;
    try { localStorage.setItem("resolveflow-theme", value); } catch { /* In-memory theme still works when storage is blocked. */ }
    window.dispatchEvent(new Event("resolveflow-theme"));
  }
export function ThemeSwitcher() {
  const theme = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  return <div className="theme-switcher" role="group" aria-label="Color theme">
    {(["light", "dark"] as const).map(value => <button type="button" key={value} data-mode={value} aria-pressed={theme === value} aria-label={`${value === "light" ? "Light" : "Dark"} theme`} onClick={() => select(value)}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">{value === "light" ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></> : <path d="M20.5 14A9 9 0 0 1 10 3.5 9 9 0 1 0 20.5 14Z" />}</svg>
      {value === "light" ? "Light" : "Dark"}
    </button>)}
  </div>;
}
