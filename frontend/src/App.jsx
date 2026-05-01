import './App.css'

function App() {
  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-icon">⬡</span>
          <span className="brand-name">LogMind</span>
          <span className="brand-tag">Incident Assistant</span>
        </div>
        <div className="header-status">
          <span className="status-dot" />
          <span className="text-muted" style={{ fontSize: '0.8rem' }}>Backend connecting…</span>
        </div>
      </header>

      {/* ── Main content placeholder ── */}
      <main className="app-main">
        <div className="hero fade-in">
          <h1>Multi-Modal Graph RAG</h1>
          <p>
            Upload logs, metrics, and dashboard screenshots — then ask natural-language
            questions to get AI-powered root cause analysis.
          </p>
          <div className="hero-badges">
            <span className="badge badge-log">📄 Text Logs</span>
            <span className="badge badge-metrics">📈 Metrics CSV/JSON</span>
            <span className="badge badge-image">🖼 Dashboard Images</span>
          </div>
          <div className="hero-note card card-sm">
            <span className="text-subtle mono" style={{ fontSize: '0.8rem' }}>
              Phase 0 scaffold — UI panels coming in Phase 3
            </span>
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <span className="text-subtle" style={{ fontSize: '0.75rem' }}>
          LogMind v0.1.0 · Multi-Modal Graph RAG Incident Assistant
        </span>
      </footer>
    </div>
  )
}

export default App
