/**
 * ResultsPanel – full RCA output display:
 *  • Answer text (main narrative)
 *  • Root cause highlight box
 *  • Confidence badge + affected services
 *  • Timeline (vertical steps)
 *  • Evidence cards
 *  • Recommendations (numbered)
 *  • AgentTrace (collapsible)
 */
import EvidenceCard from './EvidenceCard'
import AgentTrace   from './AgentTrace'
import './ResultsPanel.css'

const CONF_CLASS = { high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }
const CONF_ICONS = { high: '🟢', medium: '🟡', low: '🔴' }

export default function ResultsPanel({ result }) {
  if (!result) return null

  const {
    answer           = '',
    root_cause       = '',
    summary          = '',
    confidence       = 'low',
    affected_services= [],
    timeline         = [],
    evidence         = [],
    recommendations  = [],
    agent_trace      = [],
  } = result

  return (
    <section className="results-panel fade-in" aria-label="Analysis Results">

      {/* ── Answer ── */}
      <div className="card results-card">
        <div className="results-header">
          <h3>Incident Analysis</h3>
          <span className={`badge ${CONF_CLASS[confidence] || 'badge-low'}`}>
            {CONF_ICONS[confidence]} {confidence} confidence
          </span>
        </div>
        <p className="results-answer">{answer || summary}</p>
      </div>

      {/* ── Root Cause ── */}
      {root_cause && (
        <div className="root-cause-box fade-in">
          <div className="rc-label">⚡ Root Cause</div>
          <p className="rc-text">{root_cause}</p>
        </div>
      )}

      {/* ── Affected Services ── */}
      {affected_services.length > 0 && (
        <div className="card results-card">
          <h3>Affected Services</h3>
          <div className="services-chips">
            {affected_services.map(s => (
              <span key={s} className="badge badge-log service-chip">{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── Timeline ── */}
      {timeline.length > 0 && (
        <div className="card results-card">
          <h3>Incident Timeline</h3>
          <ol className="timeline-list">
            {timeline.map((event, i) => (
              <li key={i} className="timeline-item">
                <span className="timeline-num">{i + 1}</span>
                <span className="timeline-text">{event}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* ── Evidence ── */}
      {evidence.length > 0 && (
        <div className="card results-card">
          <h3>Retrieved Evidence <span className="count-badge">{evidence.length}</span></h3>
          <div className="evidence-grid">
            {evidence.map((item, i) => (
              <EvidenceCard key={i} item={item} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* ── Recommendations ── */}
      {recommendations.length > 0 && (
        <div className="card results-card">
          <h3>Recommendations</h3>
          <ol className="recs-list">
            {recommendations.map((r, i) => (
              <li key={i} className="rec-item">
                <span className="rec-num">{i + 1}</span>
                <span className="rec-text">{r}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* ── Agent Trace ── */}
      {agent_trace.length > 0 && (
        <div className="card results-card">
          <AgentTrace trace={agent_trace} />
        </div>
      )}

    </section>
  )
}
