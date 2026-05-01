/**
 * ChatMessage – renders a single user or assistant message in the chat feed
 */
import './ChatMessage.css'

const CONFIDENCE_CONFIG = {
  high:   { label: 'High',   cls: 'conf-high'   },
  medium: { label: 'Medium', cls: 'conf-medium'  },
  low:    { label: 'Low',    cls: 'conf-low'     },
}

function UserMessage({ content }) {
  return (
    <div className="cm-row cm-row-user">
      <div className="cm-bubble-user">{content}</div>
      <div className="cm-avatar cm-avatar-user">👤</div>
    </div>
  )
}

function AssistantMessage({ content, onViewTab }) {
  if (!content || typeof content !== 'object') return null

  const {
    answer, root_cause, summary, confidence = 'low',
    affected_services = [], recommendations = [],
    evidence = [], timeline = [], agent_trace = [],
  } = content

  const confCfg = CONFIDENCE_CONFIG[confidence] || CONFIDENCE_CONFIG.low
  const displayText = answer || summary || root_cause || 'Analysis complete.'
  const evidenceCount = evidence.length
  const timelineCount = timeline.length
  const traceCount    = agent_trace.length

  return (
    <div className="cm-row cm-row-assistant">
      <div className="cm-avatar cm-avatar-assistant">🧠</div>
      <div className="cm-card">
        {/* Answer text */}
        <p className="cm-answer">{displayText}</p>

        {/* Root cause highlight */}
        {root_cause && root_cause !== displayText && (
          <div className="cm-root-cause">
            <span className="cm-rc-label">⚡ Root Cause</span>
            <p className="cm-rc-text">{root_cause}</p>
          </div>
        )}

        {/* Footer: confidence + services */}
        <div className="cm-footer">
          <span className={`cm-conf-badge ${confCfg.cls}`}>
            <span className="cm-conf-dot" />
            {confCfg.label} confidence
          </span>
          <div className="cm-services">
            {affected_services.slice(0, 4).map(s => (
              <span key={s} className="cm-service-chip">{s}</span>
            ))}
            {affected_services.length > 4 && (
              <span className="cm-service-chip cm-service-more">+{affected_services.length - 4}</span>
            )}
          </div>
        </div>

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <ul className="cm-recs">
            {recommendations.slice(0, 3).map((r, i) => (
              <li key={i} className="cm-rec-item">
                <span className="cm-rec-num">{i + 1}</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}

        {/* View sidebar buttons */}
        <div className="cm-actions">
          {evidenceCount > 0 && (
            <button className="cm-action-btn" onClick={() => onViewTab('evidence')} id="btn-view-evidence">
              📄 Evidence {evidenceCount}
            </button>
          )}
          {timelineCount > 0 && (
            <button className="cm-action-btn" onClick={() => onViewTab('timeline')} id="btn-view-timeline">
              ⏱ Timeline {timelineCount}
            </button>
          )}
          <button className="cm-action-btn" onClick={() => onViewTab('graph')} id="btn-view-graph">
            🕸 Graph
          </button>
          {traceCount > 0 && (
            <button className="cm-action-btn" onClick={() => onViewTab('trace')} id="btn-view-trace">
              🔍 Trace {traceCount}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ThinkingMessage() {
  return (
    <div className="cm-row cm-row-assistant">
      <div className="cm-avatar cm-avatar-assistant">🧠</div>
      <div className="cm-card cm-thinking">
        <div className="cm-dots">
          <span /><span /><span />
        </div>
        <span className="cm-thinking-label">Analyzing…</span>
      </div>
    </div>
  )
}

export default function ChatMessage({ message, onViewTab }) {
  if (message.role === 'thinking') return <ThinkingMessage />
  if (message.role === 'user') return <UserMessage content={message.content} />
  return <AssistantMessage content={message.content} onViewTab={onViewTab} />
}
