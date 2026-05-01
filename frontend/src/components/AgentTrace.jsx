/**
 * AgentTrace – collapsible timeline of agent steps.
 * Shows which agent ran which action and what it returned.
 */
import { useState } from 'react'

const AGENT_COLORS = {
  retrieval_agent: 'var(--color-primary)',
  rca_agent:       'var(--color-warning)',
  orchestrator:    'var(--color-success)',
}

const AGENT_LABELS = {
  retrieval_agent: 'Retrieval',
  rca_agent:       'RCA',
  orchestrator:    'Orchestrator',
}

export default function AgentTrace({ trace }) {
  const [open, setOpen] = useState(false)
  if (!trace || trace.length === 0) return null

  return (
    <div className="agent-trace">
      <button className="trace-toggle" onClick={() => setOpen(o => !o)}>
        <span className="flex items-center gap-2">
          <span>🔍</span>
          <span>Agent Trace</span>
          <span className="trace-count">{trace.length} steps</span>
        </span>
        <span className="trace-chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="trace-body fade-in">
          {trace.map((ev, i) => {
            const color = AGENT_COLORS[ev.agent] || '#71717a'
            const label = AGENT_LABELS[ev.agent] || ev.agent
            return (
              <div className="trace-row" key={i}>
                <div className="trace-line-wrap">
                  <div className="trace-dot" style={{ background: color }} />
                  {i < trace.length - 1 && <div className="trace-connector" />}
                </div>
                <div className="trace-info">
                  <span className="trace-agent" style={{ color }}>{label}</span>
                  <span className="trace-action">{ev.action}</span>
                  <span className="trace-result">{String(ev.result || '').slice(0, 120)}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
