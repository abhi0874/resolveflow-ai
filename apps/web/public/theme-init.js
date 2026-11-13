// Runs before first paint; stored preference wins, otherwise follow the system.
(() => {
  const system = () => matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  let saved;
  try { saved = localStorage.getItem("resolveflow-theme"); } catch { /* Storage may be unavailable. */ }
  document.documentElement.dataset.theme = saved === "light" || saved === "dark" ? saved : system();
  document.documentElement.dataset.themePreference = saved === "light" || saved === "dark" ? saved : "system";
})();
