import Link from "next/link";
import { Icon } from "@/components/ui/icon";
export function WorkflowOverview() {
  return <div className="workflow-art" aria-label="Illustrated synthetic support workflow">
    <div className="preview-window">
      <div className="preview-bar"><span className="preview-brand"><Icon name="spark" width="17" height="17" /> ResolveFlow</span><span className="preview-status"><i /> EXAMPLE WORKSPACE</span></div>
      <div className="preview-request"><div className="preview-avatar">JM</div><div><span className="eyebrow">INCOMING REQUEST · DEMO-001</span><h3>Can I request a refund?</h3><p>“I upgraded last week. What are my options?”</p></div><span aria-hidden="true">↗</span></div>
      <div className="preview-pipeline"><div><Icon name="classify" /><span>Classify</span></div><span aria-hidden="true">→</span><div><Icon name="search" /><span>Retrieve</span></div><span aria-hidden="true">→</span><div><Icon name="workflow" /><span>Draft</span></div><span aria-hidden="true">→</span><div className="preview-active"><Icon name="review" /><span>Review</span></div></div>
      <div className="preview-evidence"><span className="eyebrow">01 / RELEVANT KNOWLEDGE</span><div><strong>Refund Policy</strong><span className="preview-tag">Source matched</span></div><p>Refunds may be requested within 14 days of purchase.</p></div>
      <div className="preview-answer"><div className="card-heading"><span className="eyebrow">02 / GROUNDED DRAFT</span><Icon name="spark" width="18" /></div><p>Happy to help. Your request falls within the policy’s 14-day window. Let’s review the purchase details.</p><span className="preview-citation">[refund-1] · Authored illustration</span></div>
      <div className="preview-review"><span><span className="small-dot" /> Waiting for a human decision</span><Link href="/demo/workflows/billing" aria-label="Inspect the illustrated workflow">Inspect <span aria-hidden="true">↗</span></Link></div>
    </div><div className="preview-caption"><span>01 — FROM REQUEST TO REVIEW</span><span>Illustrated workflow · no live inference</span></div>
  </div>;
}
