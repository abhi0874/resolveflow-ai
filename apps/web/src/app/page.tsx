import Link from "next/link";
import { appMode } from "@/lib/app-mode";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { WorkflowOverview } from "@/components/home/workflow-overview";
import { FeatureOverview } from "@/components/home/feature-overview";
import { ApiStatus } from "@/components/home/api-status";
import { Icon } from "@/components/ui/icon";

export default function Home() {
  return (
    <div id="top">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <SiteHeader />
      <main id="main-content">
        <section className="hero container" aria-labelledby="hero-title">
          <div className="hero-copy">
            <span className="release-badge">
              <span className="small-dot" /> CONTEXT. CLARITY. HUMAN JUDGMENT.
            </span>
            <h1 id="hero-title">
              Support with clarity.
              <br />
              <span>Resolved with care.</span>
            </h1>
            <p className="hero-description">
              Bring every request into focus. Explore how classification,
              grounded knowledge and human review turn a busy queue into
              thoughtful support.
            </p>
            <div className="hero-actions">
              <Link href="/demo" className="primary-link">
                Explore Live Demo <Icon name="arrow" width="19" height="19" />
              </Link>
              <Link href="/demo/architecture" className="hero-secondary">Explore the engineering <span aria-hidden="true">↗</span></Link>
            </div>
            <p className="hero-footnote">An interactive, synthetic workspace. No account or live AI required.</p>
          </div>
          <WorkflowOverview />
        </section>
        <div className="principles-strip">
          <div className="container">
            <span>CONSIDERED BY DESIGN</span>
            <p>Context before answers.</p>
            <span aria-hidden="true">✳</span>
            <p>Clarity at every step.</p>
            <span aria-hidden="true">✳</span>
            <p>People at the center.</p>
          </div>
        </div>
        <FeatureOverview />
        <section
          className="approach container"
          id="approach"
          aria-labelledby="approach-title"
        >
          <div className="approach-symbol" aria-hidden="true">
            <Icon name="review" width="52" height="52" />
          </div>
          <div>
            <span className="eyebrow">AUTOMATION WITH ACCOUNTABILITY</span>
            <h2 id="approach-title">
              AI moves the work forward.
              <br />
              People make the final call.
            </h2>
          </div>
          <p>
            We’re building for support teams who value both speed and care.
            Grounded knowledge, transparent workflows, and human verification
            are at the heart of the application.
          </p>
        </section>
        <section
          id="foundation"
          className="foundation container"
          aria-labelledby="foundation-title"
        >
          <div>
            <span className="eyebrow">WHERE WE ARE TODAY</span>
            <h2 id="foundation-title">Explore the product. Understand the engineering.</h2>
            <p>
              Ticket management, durable AI workflows, human review and workspace analytics are implemented. Explore their behavior in a self-contained synthetic demo; the full backend runs separately.
            </p>
          </div>
          <Link className="primary-link" href="/demo/architecture">Under the hood <Icon name="arrow" width="18" height="18" /></Link>
          {process.env.NODE_ENV === "development" && appMode() === "full" ? <ApiStatus /> : null}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
