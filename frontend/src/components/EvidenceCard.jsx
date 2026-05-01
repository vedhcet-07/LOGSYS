/**
 * EvidenceCard – displays a single retrieved evidence item
 * (log chunk, metrics summary, or image vision extract).
 */
const ICONS = { log: '📄', metrics: '📊', image: '🖼️' }
const BADGE = { log: 'badge-log', metrics: 'badge-metrics', image: 'badge-image' }

export default function EvidenceCard({ item, index }) {
  const icon  = ICONS[item.type]  || '📎'
  const badge = BADGE[item.type] || 'badge-log'
  const pct   = item.score > 0 ? Math.round(item.score * 100) : null

  return (
    <div className="evidence-card fade-in" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="ev-header">
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className={`badge ${badge}`}>{item.type}</span>
          <span className="ev-source mono">{item.source}</span>
        </div>
        {pct !== null && (
          <span className="ev-score">relevance {pct}%</span>
        )}
      </div>
      <pre className="ev-snippet">{(item.snippet || 'No snippet available').slice(0, 380)}</pre>
    </div>
  )
}
