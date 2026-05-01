/**
 * LogMind – Main Application
 * Layout: sticky header | two-column body (left: upload+query, right: results+graph)
 */
import { useState, useEffect, useCallback } from 'react'
import UploadPanel  from './components/UploadPanel'
import QueryPanel   from './components/QueryPanel'
import ResultsPanel from './components/ResultsPanel'
import GraphPanel   from './components/GraphPanel'
import './App.css'

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking')   // checking | ok | error
  const [ingestDone,    setIngestDone]    = useState(false)
  const [queryResult,   setQueryResult]   = useState(null)
  const [graphData,     setGraphData]     = useState({ nodes: [], edges: [] })

  // Health-check on mount and every 30 s
  const checkHealth = useCallback(async () => {
    try {
      const { checkHealth: ch } = await import('./services/api')
      const r = await ch()
      setBackendStatus(r.status === 'ok' ? 'ok' : 'error')
    } catch {
      setBackendStatus('error')
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const t = setInterval(checkHealth, 30_000)
    return () => clearInterval(t)
  }, [checkHealth])

  // Refresh graph whenever ingest completes
  const refreshGraph = useCallback(async () => {
    try {
      const { getGraph } = await import('./services/api')
      const data = await getGraph()
      setGraphData(data)
    } catch { /* ignore */ }
  }, [])

  const handleIngestDone = useCallback((result) => {
    setIngestDone(true)
    refreshGraph()
  }, [refreshGraph])

  const handleQueryResult = useCallback((result) => {
    setQueryResult(result)
    // also refresh graph after query (graph may grow)
    refreshGraph()
    // Scroll result into view on mobile
    if (window.innerWidth < 900) {
      setTimeout(() => {
        document.getElementById('results-anchor')?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    }
  }, [refreshGraph])

  const statusDot = {
    checking: { label: 'Connecting…', cls: 'status-checking' },
    ok:       { label: 'Backend Live',  cls: 'status-ok'       },
    error:    { label: 'Backend Offline', cls: 'status-error'  },
  }[backendStatus]

  return (
    <div className="app" id="app-root">
      {/* ── Header ── */}
      <header className="app-header" role="banner">
        <div className="header-inner">
          <div className="header-brand">
            <span className="brand-icon">🧠</span>
            <span className="brand-name">LogMind</span>
            <span className="brand-tag">Multi-Modal Graph RAG Incident Assistant</span>
          </div>
          <div className={`status-pill ${statusDot.cls}`}>
            <span className="status-dot" />
            {statusDot.label}
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <main className="app-body" role="main">
        {/* Left column */}
        <div className="left-col">
          <UploadPanel
            onIngestDone={handleIngestDone}
            onFilesChanged={() => {}}
          />
          <QueryPanel
            onResult={handleQueryResult}
            disabled={backendStatus !== 'ok'}
          />
        </div>

        {/* Right column */}
        <div className="right-col">
          <div id="results-anchor" />
          {queryResult ? (
            <ResultsPanel result={queryResult} />
          ) : (
            <div className="results-placeholder card">
              <div className="placeholder-icon">🔎</div>
              <h4>No analysis yet</h4>
              <p className="text-subtle">
                Upload your log, metrics, and screenshot files,<br />
                then ask a question to run the incident analysis.
              </p>
              <div className="placeholder-steps">
                <div className="ps-step">
                  <span className="ps-num">1</span>
                  <span>Upload files (drag &amp; drop)</span>
                </div>
                <div className="ps-step">
                  <span className="ps-num">2</span>
                  <span>Click <strong>Ingest Files</strong></span>
                </div>
                <div className="ps-step">
                  <span className="ps-num">3</span>
                  <span>Type a question &amp; click <strong>Analyze</strong></span>
                </div>
              </div>
            </div>
          )}

          <GraphPanel graphData={graphData} />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        LogMind © 2024 &nbsp;·&nbsp; Multi-Modal Graph RAG &nbsp;·&nbsp;
        Built with FastAPI · React · Pinecone · Gemini
      </footer>
    </div>
  )
}
