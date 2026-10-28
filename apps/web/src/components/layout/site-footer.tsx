import { Brand } from "./brand";

export function SiteFooter() {
  return (
    <footer className="site-footer container">
      <Brand />
      <p>Built with intention. Designed around people.</p>
      <span className="footer-label">Synthetic demo · Human-centered engineering</span>
    </footer>
  );
}
