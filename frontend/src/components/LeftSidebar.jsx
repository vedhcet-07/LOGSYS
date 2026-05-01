/**
 * LeftSidebar – Session list + file upload for active session
 */
import { useState, useRef } from 'react'
import './LeftSidebar.css'

const EXAMPLE_QUERIES = [
  'Why did auth-service fail at 2:31 AM?',
  'What caused the database connection pool exhaustion?',
  'Analyze the latency spike in the payment service',
]

export default function LeftSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onFilesIngested,
  backendOk,
}) {
  const [ingesting,    setIngesting]    = useState(false)
  const [dragOver,     setDragOver]     = useState(false)
  const [stagedFiles,  setStagedFiles]  = useState([])
  const [ingestResult, setIngestResult] = useState(null)
  const fileInputRef = useRef(null)

  const activeSession = sessions.find(s => s.id === activeSessionId)

  // ── File staging ────────────────────────────────────────────────────────────
  const ALLOWED = ['.log', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.csv', '.json']
  const allowed = (f) => ALLOWED.some(ext => f.name.toLowerCase().endsWith(ext))

  const stageFiles = (files) => {
    const valid = Array.from(files).filter(allowed)
    setStagedFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...valid.filter(f => !existing.has(f.name))]
    })
    setIngestResult(null)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    stageFiles(e.dataTransfer.files)
  }

  // ── Ingest ──────────────────────────────────────────────────────────────────
  const handleIngest = async () => {
    if (!activeSessionId || stagedFiles.length === 0) return
    setIngesting(true)
    setIngestResult(null)
    try {
      const { sessionIngest } = await import('../services/api')
      const result = await sessionIngest(activeSessionId, stagedFiles)
      setIngestResult(result)
      setStagedFiles([])
      if (onFilesIngested) onFilesIngested(result)
    } catch (err) {
      setIngestResult({ error: err.response?.data?.detail || err.message })
    } finally {
      setIngesting(false)
    }
  }

  // ── Session helpers ──────────────────────────────────────────────────────────
  const formatDate = (iso) => {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <aside className="left-sidebar" aria-label="Sessions">
      {/* Header */}
      <div className="ls-header">
        <span className="ls-title">Sessions</span>
        <button
          className="ls-new-btn"
          onClick={onNewSession}
          disabled={!backendOk}
          title="New session"
          id="btn-new-session"
        >
          + New
        </button>
      </div>

      {/* Session list */}
      <div className="ls-sessions">
        {sessions.length === 0 ? (
          <div className="ls-empty">
            <div className="ls-empty-icon">🗂️</div>
            <p>No sessions yet</p>
            <p className="ls-empty-hint">Click <strong>+ New</strong> to start</p>
          </div>
        ) : (
          sessions.map(s => (
            <div
              key={s.id}
              className={`ls-session-card${s.id === activeSessionId ? ' ls-session-active' : ''}`}
              onClick={() => onSelectSession(s.id)}
              id={`session-card-${s.id.slice(0, 8)}`}
            >
              <div className="ls-session-name" title={s.name}>{s.name}</div>
              <div className="ls-session-meta">
                <span className="ls-session-date">{formatDate(s.created_at)}</span>
                {s.node_count > 0 && (
                  <span className="ls-badge">{s.node_count} nodes</span>
                )}
                {s.files?.length > 0 && (
                  <span className="ls-badge ls-badge-files">{s.files.length} files</span>
                )}
              </div>
              <button
                className="ls-delete-btn"
                onClick={e => { e.stopPropagation(); onDeleteSession(s.id) }}
                title="Delete session"
                aria-label="Delete session"
              >✕</button>
            </div>
          ))
        )}
      </div>

      {/* Upload zone — only shown when a session is selected */}
      {activeSessionId && (
        <div className="ls-upload-section">
          <div className="ls-section-label">
            Upload to <em>{activeSession?.name || 'session'}</em>
          </div>

          <div
            className={`ls-drop-zone${dragOver ? ' ls-drop-active' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            id="upload-drop-zone"
          >
            <span className="ls-drop-icon">📁</span>
            <span className="ls-drop-text">
              {dragOver ? 'Drop files here' : 'Drop or click to add files'}
            </span>
            <span className="ls-drop-hint">.log · .json · .csv · .png</span>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".log,.txt,.json,.csv,.png,.jpg,.jpeg,.webp"
            style={{ display: 'none' }}
            onChange={e => stageFiles(e.target.files)}
            id="file-input-hidden"
          />

          {/* Staged files list */}
          {stagedFiles.length > 0 && (
            <div className="ls-staged">
              {stagedFiles.map((f, i) => (
                <div key={i} className="ls-staged-file">
                  <span className="ls-file-icon">{f.name.endsWith('.png') || f.name.endsWith('.jpg') ? '🖼️' : f.name.endsWith('.log') || f.name.endsWith('.txt') ? '📄' : '📊'}</span>
                  <span className="ls-file-name" title={f.name}>{f.name}</span>
                  <button
                    className="ls-file-remove"
                    onClick={() => setStagedFiles(prev => prev.filter((_, j) => j !== i))}
                  >✕</button>
                </div>
              ))}
            </div>
          )}

          {/* Ingest button */}
          {stagedFiles.length > 0 && (
            <button
              className="btn btn-primary w-full"
              onClick={handleIngest}
              disabled={ingesting}
              id="btn-ingest"
            >
              {ingesting ? (
                <><div className="spinner" style={{width:14,height:14}} /> Ingesting…</>
              ) : (
                `Ingest ${stagedFiles.length} file${stagedFiles.length > 1 ? 's' : ''}`
              )}
            </button>
          )}

          {/* Ingest result */}
          {ingestResult && (
            <div className={`ls-ingest-result${ingestResult.error ? ' ls-ingest-error' : ' ls-ingest-ok'}`}>
              {ingestResult.error
                ? `Error: ${ingestResult.error}`
                : `Done — ${ingestResult.graph_nodes} nodes, ${ingestResult.chunks_indexed} chunks`}
            </div>
          )}
        </div>
      )}

      {/* Example queries hint */}
      {!activeSessionId && (
        <div className="ls-hints">
          <div className="ls-section-label">Example queries</div>
          {EXAMPLE_QUERIES.map((q, i) => (
            <div key={i} className="ls-hint-chip">{q}</div>
          ))}
        </div>
      )}
    </aside>
  )
}
