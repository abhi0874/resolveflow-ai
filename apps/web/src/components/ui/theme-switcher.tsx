"use client";
import { useSyncExternalStore } from "react";
type Theme = "light" | "dark" | "system";
function apply(value: Theme) {
  const root = document.documentElement;
  root.dataset.themePreference = value;
  root.dataset.theme = value === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : value;
}
function snapshot(): Theme { return (document.documentElement.dataset.themePreference as Theme) || "system"; }
function subscribe(update: () => void) {
  const media = matchMedia("(prefers-color-scheme: dark)");
  function system() { if (snapshot() === "system") { apply("system"); update(); } }
  function storage(event: StorageEvent) {
    if (event.key !== "resolveflow-theme" && event.key !== null) return;
    apply(event.newValue === "light" || event.newValue === "dark" ? event.newValue : "system"); update();
  }
  window.addEventListener("resolveflow-theme", update); window.addEventListener("storage", storage); media.addEventListener("change", system);
  return () => { window.removeEventListener("resolveflow-theme", update); window.removeEventListener("storage", storage); media.removeEventListener("change", system); };
}
const serverSnapshot = (): Theme => "system";
export function ThemeSwitcher() {
  const theme = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  function select(value: Theme) {
    apply(value); try { localStorage.setItem("resolveflow-theme", value); } catch { /* Keep the in-memory preference. */ }
    window.dispatchEvent(new Event("resolveflow-theme"));
  }
  return <div className="theme-switcher" role="group" aria-label="Color theme">
    {(["light", "dark", "system"] as const).map(value => <button type="button" key={value} data-mode={value} aria-pressed={theme === value} aria-label={`${value[0].toUpperCase() + value.slice(1)} theme`} onClick={() => select(value)}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">{value === "light" ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></> : value === "dark" ? <path d="M20.5 14A9 9 0 0 1 10 3.5 9 9 0 1 0 20.5 14Z" /> : <><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8m-4-4v4" /></>}</svg>
      <span>{value[0].toUpperCase() + value.slice(1)}</span>
    </button>)}
  </div>;
}
