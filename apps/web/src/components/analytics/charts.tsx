"use client";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { count, label, type Bucket, type Point } from "@/lib/analytics";

export function TrendChart({ title, points }: { title: string; points: Point[] }) {
  const total = points.reduce((sum, point) => sum + point.count, 0);
  return <section className="workspace-card analytics-chart" aria-label={title}>
    <div className="card-heading"><h2>{title}</h2><span className="role-badge">UTC · daily</span></div>
    {total === 0 ? <p className="analytics-empty">No recorded activity in this range.</p> : <>
      <div className="analytics-plot" role="group" aria-label={`${title}: ${count(total)} records. Data table follows.`}>
        <ResponsiveContainer width="100%" height="100%" minWidth={1}>
          <AreaChart data={points} accessibilityLayer margin={{ top: 12, right: 12, left: -24, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="day" tickFormatter={day => day.slice(5)} minTickGap={40} stroke="var(--muted)" fontSize={12} />
            <YAxis allowDecimals={false} stroke="var(--muted)" fontSize={12} />
            <Tooltip contentStyle={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--foreground)" }} />
            <Area type="linear" dataKey="count" name="Records" stroke="var(--accent)" fill="var(--accent-soft)" strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details className="analytics-data"><summary>View {title.toLowerCase()} data</summary>
        <div className="analytics-table-scroll"><table><caption>{title} by UTC date</caption><thead><tr><th scope="col">Date</th><th scope="col">Count</th></tr></thead>
          <tbody>{points.map(point => <tr key={point.day}><th scope="row">{point.day}</th><td>{count(point.count)}</td></tr>)}</tbody></table></div>
      </details>
    </>}
  </section>;
}

export function Distribution({ title, buckets, note }: { title: string; buckets: Bucket[]; note?: string }) {
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0);
  return <section className="workspace-card analytics-distribution" aria-label={title}>
    <h2>{title}</h2>{note && <p className="field-help">{note}</p>}
    {!total && <p className="analytics-empty">No records in this selection.</p>}
    <ul>{buckets.map(bucket => <li key={bucket.label}>
      <div><span>{label(bucket.label)}</span><strong>{count(bucket.count)}</strong></div>
      <div className="analytics-track" aria-hidden="true"><span style={{ width: `${total ? bucket.count / total * 100 : 0}%` }} /></div>
    </li>)}</ul>
  </section>;
}
