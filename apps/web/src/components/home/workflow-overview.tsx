import { Icon, type IconName } from "@/components/ui/icon";

const steps: { title: string; detail: string; icon: IconName }[] = [
  {
    title: "Understand the request",
    detail: "Classify intent & priority",
    icon: "classify",
  },
  {
    title: "Find the right context",
    detail: "Retrieve relevant knowledge",
    icon: "search",
  },
  {
    title: "Bring it all together",
    detail: "Orchestrate a grounded response",
    icon: "workflow",
  },
  {
    title: "Keep people in control",
    detail: "Review, refine & approve",
    icon: "review",
  },
];

export function WorkflowOverview() {
  return (
    <div className="workflow-art">
      <div className="orbit orbit-one" aria-hidden="true" />
      <div className="orbit orbit-two" aria-hidden="true" />
      <div className="workflow-card">
        <div className="workflow-heading">
          <span className="eyebrow">A REQUEST, CONSIDERED</span>
          <Icon name="spark" width="18" height="18" />
        </div>
        <ol className="workflow-steps">
          {steps.map((step, index) => (
            <li key={step.title}>
              <span
                className={`step-icon ${index === 3 ? "step-icon-final" : ""}`}
              >
                <Icon name={step.icon} />
              </span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </div>
              <span className="step-number">0{index + 1}</span>
            </li>
          ))}
        </ol>
        <div className="workflow-caption">
          <span className="small-dot" /> Illustrated workflow · no live inference
        </div>
      </div>
      <div className="human-note">
        <Icon name="review" width="18" height="18" />
        <span>Intelligence, with a human touch.</span>
      </div>
    </div>
  );
}
