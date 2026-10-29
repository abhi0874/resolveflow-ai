import { ThemeSwitcher } from "@/components/ui/theme-switcher";
import Link from "next/link";
import { appMode } from "@/lib/app-mode";
import { Brand } from "./brand";
import { Icon } from "@/components/ui/icon";

export function SiteHeader() {
  return (
    <header className="site-header container">
      <Brand />
      <nav aria-label="Main navigation" className="main-nav">
        <a className="section-capsule" href="#capabilities">Capabilities</a>
        <a className="section-capsule" href="#approach">Our approach</a>
        <Link className="section-capsule" href="/demo/architecture">Engineering</Link>
      </nav>
      <ThemeSwitcher />
      <a className="header-link" href={appMode() === "demo" ? "/demo" : "/login"}>
        {appMode() === "demo" ? "Explore demo" : "Sign in"} <Icon name="arrow" width="16" height="16" />
      </a>
    </header>
  );
}
