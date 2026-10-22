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
              <span className="small-dot" /> THE FOUNDATION FOR BETTER SUPPORT
            </span>
            <h1 id="hero-title">
              Intelligent Customer Support,
              <br />
              <span>Powered by AI.</span>
            </h1>
            <p className="hero-description">
              An AI-powered customer support operations platform combining
              machine learning, knowledge retrieval, and intelligent workflow
              orchestration.
            </p>
            <div className="hero-actions">
              <Link href="/demo" className="primary-link">
                Explore Live Demo <Icon name="arrow" width="19" height="19" />
              </Link>
              <span className="development-note">
                In development
                <br />
                <strong>Interactive synthetic workspace.</strong>
              </span>
            </div>
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
            are at the heart of the plan.
          </p>
        </section>
        <section
          id="foundation"
          className="foundation container"
          aria-labelledby="foundation-title"
        >
          <div>
            <span className="eyebrow">WHERE WE ARE TODAY</span>
            <h2 id="foundation-title">A foundation. A clear direction.</h2>
            <p>
              Ticket management, durable AI workflows, human review and workspace analytics are implemented. Explore their behavior in a self-contained synthetic demo; the full backend runs separately.
            </p>
          </div>
          <span className="foundation-version">13 / INTERACTIVE DEMO</span>
          {process.env.NODE_ENV === "development" && appMode() === "full" ? <ApiStatus /> : null}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
