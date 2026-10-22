import { appMode } from "@/lib/app-mode";
import { Brand } from "./brand";
import { Icon } from "@/components/ui/icon";

export function SiteHeader() {
  return (
    <header className="site-header container">
      <Brand />
      <nav aria-label="Main navigation" className="main-nav">
        <a href="#capabilities">Capabilities</a>
        <a href="#approach">Our approach</a>
      </nav>
      <a className="header-link" href={appMode() === "demo" ? "/demo" : "/login"}>
        {appMode() === "demo" ? "Explore demo" : "Sign in"} <Icon name="arrow" width="16" height="16" />
      </a>
    </header>
  );
}
