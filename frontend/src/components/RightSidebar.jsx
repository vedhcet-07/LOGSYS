/**
 * RightSidebar – Phase 4D polished version
 * Tabs: Evidence · Timeline · Graph · Trace
 * - Evidence sorted by score
 * - Graph: click node → detail panel
 * - Trace: color-coded by agent with timing
 * - Skeleton loading states
 * - Robust empty states
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import './RightSidebar.css'

// ── Skeleton loader ───────────────────────────────────────────────────────────
function Skeleton({ lines = 3 }) {
  return (
    <div className="rs-skeleton">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="rs-skel-line" style={{ width: `${70 + (i % 3) * 10}%` }} />
      ))}
    </div>
  )
}

// ── Evidence tab ──────────────────────────────────────────────────────────────
function EvidenceTab({ evidence, loading }) {
  if (loading) return <div className="rs-tab-body"><Skeleton lines={6} /></div>
  if (!evidence?.length) {
    return (
      <div className="rs-empty">
        <span className="rs-empty-icon">📄</span>
        <p>No evidence retrieved</p>
        <small>Ask a question after uploading files</small>
      </div>
    )
  }

  // Sort by score descending
  const sorted = [...evidence].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))

  return (
    <div className="rs-tab-body rs-evidence-list">
      {sorted.map((ev, i) => {
        const modality = ev.type || ev.metadata?.modality || 'log'
        const source   = ev.source || ev.metadata?.source_file || 'unknown'
        const snippet  = ev.snippet || ev.metadata?.text_snippet || ''
        const score    = ev.score ?? 0
        const pct      = Math.round(score * 100)
        return (
          <div key={i} className="rs-evidence-card" style={{ animationDelay: `${i * 40}ms` }}>
            <div className="rs-ev-header">
              <span className={`badge badge-${modality}`}>{modality.toUpperCase()}</span>
              <span className="rs-ev-source" title={source}>{source}</span>
              <span className={`rs-ev-score ${pct >= 70 ? 'rs-score-high' : pct >= 40 ? 'rs-score-mid' : 'rs-score-low'}`}>
                {pct}%
              </span>
            </div>
            {/* Relevance bar */}
            <div className="rs-ev-bar">
              <div className="rs-ev-bar-fill" style={{ width: `${pct}%` }} />
            </div>
            <p className="rs-ev-snippet">{snippet.slice(0, 320)}</p>
          </div>
        )
      })}
    </div>
  )
}

// ── Timeline tab ──────────────────────────────────────────────────────────────
const ERROR_RE  = /error|fail|crash|down|exception|refused|denied/i
const WARN_RE   = /warn|spike|slow|high|exhaust|timeout|degrad/i
const INFO_RE   = /start|init|connect|listen|ready|success|restored/i

function classifyEvent(text) {
  if (ERROR_RE.test(text)) return 'error'
  if (WARN_RE.test(text))  return 'warn'
  if (INFO_RE.test(text))  return 'info'
  return 'neutral'
}

// Try to pull a timestamp from the start of the event string
function parseEvent(text) {
  const tsMatch = text.match(/(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)/)
  if (tsMatch) {
    return { ts: tsMatch[1].slice(11), body: text.replace(tsMatch[0], '').trim() }
  }
  return { ts: null, body: text }
}

function TimelineTab({ timeline, loading }) {
  if (loading) return <div className="rs-tab-body"><Skeleton lines={5} /></div>
  if (!timeline?.length) {
    return (
      <div className="rs-empty">
        <span className="rs-empty-icon">⏱</span>
        <p>No timeline events</p>
        <small>Timeline is built from log evidence</small>
      </div>
    )
  }
  return (
    <div className="rs-tab-body rs-timeline">
      {timeline.map((event, i) => {
        const kind       = classifyEvent(event)
        const { ts, body } = parseEvent(event)
        return (
          <div key={i} className={`rs-tl-item rs-tl-${kind}`} style={{ animationDelay: `${i * 35}ms` }}>
            <div className="rs-tl-line-wrap">
              <div className="rs-tl-dot" />
              {i < timeline.length - 1 && <div className="rs-tl-connector" />}
            </div>
            <div className="rs-tl-content">
              <div className="rs-tl-meta">
                <span className="rs-tl-num">{i + 1}</span>
                {ts && <span className="rs-tl-ts">{ts}</span>}
                <span className={`rs-tl-kind rs-kind-${kind}`}>{kind}</span>
              </div>
              <p className="rs-tl-text">{body}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Graph tab ─────────────────────────────────────────────────────────────────
const TYPE_COLOR = {
  service:  '#6366f1',
  database: '#34d399',
  error:    '#ef4444',
  file:     '#a78bfa',
  default:  '#71717a',
}

function GraphTab({ graphData, loading }) {
  const containerRef    = useRef(null)
  const [dims, setDims] = useState({ w: 340, h: 340 })
  const [selectedNode, setSelectedNode] = useState(null)
  const [ForceGraph,   setForceGraph]   = useState(null)
  const [graphReady,   setGraphReady]   = useState(false)

  // Lazy-load ForceGraph2D (it's heavy)
  useEffect(() => {
    import('react-force-graph-2d').then(mod => {
      setForceGraph(() => mod.default)
      setGraphReady(true)
    }).catch(e => console.warn('ForceGraph load failed', e))
  }, [])

  // ResizeObserver for responsive canvas size
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(entries => {
      const e = entries[0]
      if (e) setDims({ w: Math.floor(e.contentRect.width), h: Math.max(280, Math.floor(e.contentRect.height - 40)) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(prev => prev?.id === node.id ? null : node)
  }, [])

  if (loading) return <div className="rs-tab-body" style={{ height: 300 }}><Skeleton lines={4} /></div>

  const nodes = graphData?.nodes || []
  const edges = graphData?.edges || []

  if (!nodes.length) {
    return (
      <div className="rs-empty">
        <span className="rs-empty-icon">🕸</span>
        <p>Knowledge graph is empty</p>
        <small>Ingest log files to build the graph</small>
      </div>
    )
  }

  const gd = {
    nodes: nodes.map(n => ({
      ...n,
      id:    n.id ?? n.name ?? String(n),
      color: TYPE_COLOR[n.type] ?? TYPE_COLOR.default,
      label: n.id ?? n.name ?? '',
    })),
    links: edges.map(e => ({
      source: e.source,
      target: e.target,
      label:  e.rel || '',
    })),
  }

  return (
    <div className="rs-tab-body rs-graph-wrapper" ref={containerRef}>
      {graphReady && ForceGraph ? (
        <div className="rs-graph-canvas-wrap">
          <ForceGraph
            width={dims.w}
            height={dims.h}
            graphData={gd}
            backgroundColor="transparent"
            nodeLabel={n => `${n.label} (${n.type || 'node'})`}
            nodeColor={n => n.color}
            nodeRelSize={5}
            linkColor={() => '#3f3f46'}
            linkWidth={1.2}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.label
              const fontSize = Math.max(10, 12 / globalScale)
              ctx.beginPath()
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI)
              ctx.fillStyle = node.color
              ctx.fill()
              if (selectedNode?.id === node.id) {
                ctx.strokeStyle = '#fff'
                ctx.lineWidth = 2
                ctx.stroke()
              }
              ctx.font = `${fontSize}px Inter, sans-serif`
              ctx.fillStyle = globalScale > 1.5 ? '#fafafa' : 'rgba(250,250,250,.7)'
              ctx.textAlign = 'center'
              ctx.fillText(label, node.x, node.y + 10)
            }}
          />
        </div>
      ) : (
        <Skeleton lines={3} />
      )}

      {/* Legend */}
      <div className="rs-graph-legend">
        {Object.entries(TYPE_COLOR).filter(([k]) => k !== 'default').map(([t, c]) => (
          <span key={t} className="rs-legend-item">
            <span className="rs-legend-dot" style={{ background: c }} />{t}
          </span>
        ))}
        <span className="rs-legend-item rs-legend-hint">Click node for details</span>
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div className="rs-node-detail">
          <div className="rs-nd-header">
            <span className="rs-nd-dot" style={{ background: TYPE_COLOR[selectedNode.type] ?? TYPE_COLOR.default }} />
            <span className="rs-nd-name">{selectedNode.label || selectedNode.id}</span>
            <button className="rs-nd-close" onClick={() => setSelectedNode(null)}>✕</button>
          </div>
          <div className="rs-nd-body">
            <div className="rs-nd-row"><span>Type</span><span>{selectedNode.type || 'node'}</span></div>
            {selectedNode.modality && <div className="rs-nd-row"><span>Modality</span><span>{selectedNode.modality}</span></div>}
            {selectedNode.source_file && <div className="rs-nd-row"><span>Source</span><span>{selectedNode.source_file}</span></div>}
            <div className="rs-nd-row">
              <span>Connected edges</span>
              <span>{edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Trace tab ─────────────────────────────────────────────────────────────────
const AGENT_CONFIG = {
  retrieval_agent: { color: '#6366f1', label: 'Retrieval' },
  rca_agent:       { color: '#f59e0b', label: 'RCA' },
  orchestrator:    { color: '#22c55e', label: 'Orchestrator' },
}

function TraceTab({ trace, loading }) {
  if (loading) return <div className="rs-tab-body"><Skeleton lines={5} /></div>
  if (!trace?.length) {
    return (
      <div className="rs-empty">
        <span className="rs-empty-icon">🔍</span>
        <p>No agent trace</p>
        <small>Trace appears after running a query</small>
      </div>
    )
  }

  return (
    <div className="rs-tab-body rs-trace-list">
      {trace.map((step, i) => {
        const agentCfg = AGENT_CONFIG[step.agent] || { color: '#71717a', label: step.agent }
        const result   = step.result == null ? '' :
          typeof step.result === 'object'
            ? JSON.stringify(step.result, null, 2).slice(0, 200)
            : String(step.result).slice(0, 200)
        const isError  = step.action?.includes('error') || step.action?.includes('fail')
        return (
          <div key={i} className={`rs-trace-step${isError ? ' rs-trace-error' : ''}`} style={{ animationDelay: `${i * 30}ms` }}>
            <div className="rs-trace-header">
              <span className="rs-trace-index">{i + 1}</span>
              <span className="rs-trace-agent-badge" style={{ background: `${agentCfg.color}20`, color: agentCfg.color }}>
                {agentCfg.label}
              </span>
              <span className="rs-trace-action">{step.action}</span>
            </div>
            {result && (
              <pre className="rs-trace-result">{result}</pre>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'evidence', label: 'Evidence', icon: '📄', countKey: 'evidence' },
  { id: 'timeline', label: 'Timeline', icon: '⏱',  countKey: 'timeline' },
  { id: 'graph',    label: 'Graph',    icon: '🕸',  countKey: null       },
  { id: 'trace',    label: 'Trace',    icon: '🔍',  countKey: 'agent_trace' },
]

export default function RightSidebar({ open, activeTab, onTabChange, result, graphData, onClose, loading }) {
  if (!open) return null

  const count = (key) => !key || !result ? 0 : (result[key]?.length || 0)

  return (
    <aside className="right-sidebar" aria-label="Analysis details">
      {/* Tab bar */}
      <div className="rs-header">
        <div className="rs-tabs" role="tablist">
          {TABS.map(t => (
            <button
              key={t.id}
              role="tab"
              aria-selected={activeTab === t.id}
              className={`rs-tab${activeTab === t.id ? ' rs-tab-active' : ''}`}
              onClick={() => onTabChange(t.id)}
              id={`tab-${t.id}`}
            >
              <span className="rs-tab-icon">{t.icon}</span>
              <span className="rs-tab-label">{t.label}</span>
              {t.countKey && count(t.countKey) > 0 && (
                <span className="rs-tab-badge">{count(t.countKey)}</span>
              )}
            </button>
          ))}
        </div>
        <button className="rs-close-btn" onClick={onClose} aria-label="Close">✕</button>
      </div>

      {/* Content */}
      <div className="rs-content" role="tabpanel">
        {activeTab === 'evidence' && <EvidenceTab evidence={result?.evidence}    loading={loading} />}
        {activeTab === 'timeline' && <TimelineTab timeline={result?.timeline}    loading={loading} />}
        {activeTab === 'graph'    && <GraphTab    graphData={graphData}           loading={loading} />}
        {activeTab === 'trace'    && <TraceTab    trace={result?.agent_trace}     loading={loading} />}
      </div>
    </aside>
  )
}
