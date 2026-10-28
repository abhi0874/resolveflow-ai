// Runs before the body is painted. No cookies, network access or user data.
try {
  document.documentElement.dataset.theme = localStorage.getItem("resolveflow-theme") === "light" ? "light" : "dark";
} catch {
  document.documentElement.dataset.theme = "dark";
}
