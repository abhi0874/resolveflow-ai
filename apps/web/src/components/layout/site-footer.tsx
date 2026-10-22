import { Brand } from "./brand";

export function SiteFooter() {
  return (
    <footer className="site-footer container">
      <Brand />
      <p>Built with intention. Designed around people.</p>
      <span className="footer-label">Foundation release · v0.1.0</span>
    </footer>
  );
}
