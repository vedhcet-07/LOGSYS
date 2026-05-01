/**
 * GraphPanel – interactive knowledge-graph visualization using react-force-graph-2d.
 * Node colors are based on entity type. Handles dynamic import to avoid SSR issues.
 * Falls back gracefully to a node/edge list if the canvas library fails to load.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import './GraphPanel.css'

const NODE_COLORS = {
  service:   '#6366f1',
  error:     '#ef4444',
  database:  '#f59e0b',
  file:      '#8b5cf6',
  metric:    '#10b981',
  incident:  '#f97316',
  endpoint:  '#06b6d4',
  default:   '#52525b',
}

function nodeColor(node) {
  return NODE_COLORS[node.type] || NODE_COLORS.default
}

function nodeLabel(node) {
  return `${node.id} (${node.type || 'entity'})`
}

function buildForceData(rawGraph) {
  const nodes = (rawGraph.nodes || []).map(n => ({
    ...n,
    id:    n.id,
    label: n.id,
    color: nodeColor(n),
  }))
  const nodeSet = new Set(nodes.map(n => n.id))
  const links   = (rawGraph.edges || [])
    .filter(e => nodeSet.has(e.source) && nodeSet.has(e.target))
    .map(e => ({ source: e.source, target: e.target, label: e.rel || '' }))
  return { nodes, links }
}

export default function GraphPanel({ graphData }) {
  const containerRef   = useRef(null)
  const [FG, setFG]    = useState(null)
  const [loadErr, setLoadErr] = useState(false)
  const [selected, setSelected] = useState(null)
  const forceData = buildForceData(graphData || {})

  // Dynamic import of canvas library
  useEffect(() => {
    import('react-force-graph-2d')
      .then(m => setFG(() => m.default))
      .catch(() => setLoadErr(true))
  }, [])

  const handleNodeClick = useCallback((node) => {
    setSelected(s => s?.id === node.id ? null : node)
  }, [])

  const isEmpty = !forceData.nodes.length

  return (
    <section className="graph-panel card" aria-label="Knowledge Graph">
      <div className="graph-header">
        <h3>Knowledge Graph</h3>
        <div className="graph-stats">
          <span className="gs">{forceData.nodes.length} nodes</span>
          <span className="gs">{forceData.links.length} edges</span>
        </div>
      </div>

      {/* Legend */}
      <div className="graph-legend">
        {Object.entries(NODE_COLORS).filter(([k]) => k !== 'default').map(([type, color]) => (
          <span key={type} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>

      {/* Canvas or fallback */}
      <div className="graph-canvas" ref={containerRef}>
        {isEmpty ? (
          <div className="graph-empty">
            <div className="graph-empty-icon">🕸️</div>
            <p>Ingest files to populate the knowledge graph</p>
          </div>
        ) : loadErr ? (
          /* Fallback: plain node list */
          <div className="graph-fallback">
            <p className="text-subtle" style={{ marginBottom: '12px' }}>
              Canvas unavailable — showing text view
            </p>
            <div className="fallback-nodes">
              {forceData.nodes.map(n => (
                <span key={n.id} className="fallback-node" style={{ borderColor: n.color }}>
                  {n.id}
                </span>
              ))}
            </div>
          </div>
        ) : FG ? (
          <FG
            graphData={forceData}
            width={containerRef.current?.clientWidth || 540}
            height={320}
            backgroundColor="transparent"
            nodeLabel={nodeLabel}
            nodeColor={nodeColor}
            nodeRelSize={6}
            linkColor={() => 'rgba(113,113,122,0.4)'}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label   = node.id
              const fontSize = Math.max(10, 14 / globalScale)
              const r        = 6
              ctx.beginPath()
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
              ctx.fillStyle = node.id === selected?.id ? '#fff' : node.color
              ctx.fill()
              if (node.id === selected?.id) {
                ctx.strokeStyle = node.color
                ctx.lineWidth   = 2
                ctx.stroke()
              }
              if (globalScale > 0.8) {
                ctx.font         = `${fontSize}px Inter, sans-serif`
                ctx.fillStyle    = 'rgba(244,244,245,0.85)'
                ctx.textAlign    = 'center'
                ctx.fillText(label, node.x, node.y + r + fontSize)
              }
            }}
            cooldownTicks={80}
          />
        ) : (
          <div className="graph-loading">
            <span className="spinner" />&nbsp;Loading graph engine…
          </div>
        )}
      </div>

      {/* Selected node detail */}
      {selected && (
        <div className="node-detail fade-in">
          <span className="nd-dot" style={{ background: nodeColor(selected) }} />
          <span className="nd-id">{selected.id}</span>
          <span className="nd-type badge badge-log" style={{
            background: `${nodeColor(selected)}22`,
            borderColor: `${nodeColor(selected)}44`,
            color: nodeColor(selected)
          }}>{selected.type || 'entity'}</span>
          {Object.entries(selected).filter(([k]) =>
            !['id', 'type', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'color', 'label', 'index'].includes(k)
          ).map(([k, v]) => (
            <span key={k} className="nd-attr">{k}: {String(v)}</span>
          ))}
        </div>
      )}
    </section>
  )
}
