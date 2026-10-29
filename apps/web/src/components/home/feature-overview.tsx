import { Icon, type IconName } from "@/components/ui/icon";

const features: {
  title: string;
  description: string;
  icon: IconName;
  tag: string;
}[] = [
  {
    title: "Intelligent Ticket Classification",
    description:
      "Bring clarity to the queue with ML category suggestions and bounded rules for priority.",
    icon: "classify",
    tag: "UNDERSTAND",
  },
  {
    title: "AI-Powered Knowledge Retrieval",
    description:
      "Connect each question to relevant knowledge, with source context behind every response.",
    icon: "search",
    tag: "DISCOVER",
  },
  {
    title: "Durable Workflow Orchestration",
    description:
      "Coordinate specialized AI steps through LangGraph, from first context to a considered draft.",
    icon: "workflow",
    tag: "COORDINATE",
  },
  {
    title: "Human-in-the-Loop Verification",
    description:
      "Give your team the final say. Review, refine, and approve responses before any action.",
    icon: "review",
    tag: "VERIFY",
  },
];

export function FeatureOverview() {
  return (
    <section
      id="capabilities"
      className="capabilities container"
      aria-labelledby="capabilities-title"
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow section-capsule">A CONNECTED SUPPORT EXPERIENCE</span>
          <h2 id="capabilities-title">
            Four foundations.
            <br />
            One thoughtful workflow.
          </h2>
        </div>
        <p>
          From understanding a request to verifying a response.
          <br className="desktop-break" /> Explore the capabilities of the full application
          through clearly labeled examples.
        </p>
      </div>
      <div className="feature-grid">
        {features.map((feature, index) => (
          <article className="feature-card" key={feature.title}>
            <div className="feature-top">
              <Icon name={feature.icon} width="28" height="28" />
              <span>0{index + 1}</span>
            </div>
            <span className="feature-tag">{feature.tag}</span>
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
            <span className="planned-label">Implemented locally</span>
          </article>
        ))}
      </div>
    </section>
  );
}
