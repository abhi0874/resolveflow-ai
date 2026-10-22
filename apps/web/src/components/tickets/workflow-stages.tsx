import { workflowStages } from "@/lib/workflows";
export function WorkflowStages({ completed, current, failed, currentLabel, timings = {} }: {
  completed: string[]; current: string; failed?: string | null; currentLabel: string; timings?: Record<string, number>;
}) {
  return <ol className="workflow-stages" aria-label="Workflow stages">{workflowStages.map(([key, label], index) => {
    const done = completed.includes(key), failure = failed === key, active = current === key && !done;
    return <li key={key} data-state={failure ? "failed" : done ? "complete" : active ? "current" : "waiting"}>
      <span className="workflow-stage-number" aria-hidden="true">{done ? "✓" : index + 1}</span>
      <div><strong>{label}</strong><span>{failure ? "Failed" : done ? "Complete" : active ? currentLabel : "Not completed"}</span>
        {timings[key] !== undefined && <small>{Math.round(timings[key])} ms</small>}</div>
    </li>;
  })}</ol>;
}
