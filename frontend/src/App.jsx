/**
 * LogMind v2 – 3-column ChatGPT-style shell (Phase 4D polished)
 */
import { useState, useEffect, useCallback } from 'react'
import LeftSidebar  from './components/LeftSidebar'
import ChatWindow   from './components/ChatWindow'
import RightSidebar from './components/RightSidebar'
import { ToastContainer, addToast } from './components/Toast'
import './App.css'

let _msgId = 0
const newId = () => String(++_msgId)

export default function App() {
  // ── Backend status ─────────────────────────────────────────────────────────
  const [backendStatus, setBackendStatus] = useState('checking')

  // ── Sessions ───────────────────────────────────────────────────────────────
  const [sessions,        setSessions]        = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)

  // ── Chat state (per active session) ────────────────────────────────────────
  const [messages, setMessages] = useState([])
  const [loading,  setLoading]  = useState(false)

  // ── Right sidebar ──────────────────────────────────────────────────────────
  const [rightOpen,   setRightOpen]   = useState(false)
  const [rightTab,    setRightTab]    = useState('evidence')
  const [rightResult, setRightResult] = useState(null)
  const [graphData,   setGraphData]   = useState({ nodes: [], edges: [] })

  // ── Left sidebar toggle ────────────────────────────────────────────────────
  const [leftOpen, setLeftOpen] = useState(true)

  // ── Toasts ─────────────────────────────────────────────────────────────────
  const [toasts, setToasts] = useState([])
  const toast = useCallback((type, message) => addToast(setToasts, { type, message }), [])

  // ── Health check ───────────────────────────────────────────────────────────
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

  // ── Load session list ──────────────────────────────────────────────────────
  const refreshSessions = useCallback(async () => {
    try {
      const { listSessions } = await import('./services/api')
      const data = await listSessions()
      setSessions(data.sessions || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { refreshSessions() }, [refreshSessions])

  // ── Select a session (loads chat history + graph) ──────────────────────────
  const selectSession = useCallback(async (sessionId) => {
    setActiveSessionId(sessionId)
    setMessages([])
    setRightResult(null)
    setRightOpen(false)
    setGraphData({ nodes: [], edges: [] })
    try {
      const { sessionChat, sessionGraph } = await import('./services/api')
      const [chatData, gData] = await Promise.all([
        sessionChat(sessionId).catch(() => ({ history: [] })),
        sessionGraph(sessionId).catch(() => ({ nodes: [], edges: [] })),
      ])
      const msgs = (chatData.history || []).map(entry => ({
        id:      newId(),
        role:    entry.role,
        content: entry.content,
      }))
      setMessages(msgs)
      setGraphData(gData)
      const lastAssistant = [...msgs].reverse().find(m => m.role === 'assistant')
      if (lastAssistant) {
        setRightResult(lastAssistant.content)
      }
    } catch (err) {
      toast('error', `Failed to load session: ${err.message}`)
    }
  }, [toast])

  // ── New session ────────────────────────────────────────────────────────────
  const handleNewSession = useCallback(async () => {
    try {
      const { createSession } = await import('./services/api')
      const d    = new Date()
      const name = `Session ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`
      const sess = await createSession(name)
      await refreshSessions()
      selectSession(sess.id)
      toast('success', `Created session "${sess.name}"`)
    } catch (err) {
      toast('error', `Could not create session: ${err.message}`)
    }
  }, [refreshSessions, selectSession, toast])

  // ── Delete session ─────────────────────────────────────────────────────────
  const handleDeleteSession = useCallback(async (sessionId) => {
    const sess = sessions.find(s => s.id === sessionId)
    try {
      const { deleteSession } = await import('./services/api')
      await deleteSession(sessionId)
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setMessages([])
        setRightResult(null)
        setGraphData({ nodes: [], edges: [] })
        setRightOpen(false)
      }
      await refreshSessions()
      toast('info', `Deleted "${sess?.name || 'session'}"`)
    } catch (err) {
      toast('error', `Delete failed: ${err.message}`)
    }
  }, [activeSessionId, sessions, refreshSessions, toast])

  // ── After ingest: auto-rename session if unnamed, refresh graph ───────────
  const handleFilesIngested = useCallback(async (result, firstFileName) => {
    if (!activeSessionId) return
    try {
      const { sessionGraph } = await import('./services/api')
      const gData = await sessionGraph(activeSessionId)
      setGraphData(gData)
      toast('success', `Ingested ${result.files_processed} file(s) · ${result.graph_nodes} graph nodes`)
    } catch { /* ignore */ }
    await refreshSessions()
  }, [activeSessionId, refreshSessions, toast])

  // ── Send a query ───────────────────────────────────────────────────────────
  const handleSend = useCallback(async (query) => {
    if (!activeSessionId || loading) return

    const userMsg = { id: newId(), role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    // Show right sidebar in loading state
    setRightTab('evidence')
    setRightOpen(true)

    try {
      const { sessionQuery } = await import('./services/api')
      const result = await sessionQuery(activeSessionId, query)

      const assistantMsg = { id: newId(), role: 'assistant', content: result }
      setMessages(prev => [...prev, assistantMsg])
      setRightResult(result)

      // Refresh graph after query
      try {
        const { sessionGraph } = await import('./services/api')
        const gData = await sessionGraph(activeSessionId)
        setGraphData(gData)
      } catch { /* ignore */ }

    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Query failed'
      toast('error', `Analysis failed: ${detail}`)
      setMessages(prev => [...prev, {
        id:      newId(),
        role:    'assistant',
        content: {
          answer:            `Analysis error: ${detail}`,
          root_cause:        '',
          confidence:        'low',
          evidence:          [],
          agent_trace:       [{ agent: 'orchestrator', action: 'error', result: detail }],
          timeline:          [],
          affected_services: [],
          recommendations:   [],
        },
      }])
    } finally {
      setLoading(false)
    }
  }, [activeSessionId, loading, toast])

  // ── View a right sidebar tab ───────────────────────────────────────────────
  const handleViewTab = useCallback((tab) => {
    setRightTab(tab)
    setRightOpen(true)
  }, [])

  // ── Derived ────────────────────────────────────────────────────────────────
  const activeSession = sessions.find(s => s.id === activeSessionId) || null
  const backendOk     = backendStatus === 'ok'

  const statusDot = {
    checking: { label: 'Connecting…',    cls: 'status-checking' },
    ok:       { label: 'Backend Live',   cls: 'status-ok'       },
    error:    { label: 'Backend Offline', cls: 'status-error'   },
  }[backendStatus]

  return (
    <div className="app-shell" id="app-root">

      {/* ── Header ── */}
      <header className="app-header" role="banner">
        <div className="header-left">
          <button
            className="header-toggle-btn"
            onClick={() => setLeftOpen(o => !o)}
            title={leftOpen ? 'Hide sessions' : 'Show sessions'}
            aria-label="Toggle sessions panel"
            id="btn-toggle-left"
          >☰</button>
          <span className="brand-icon">🧠</span>
          <span className="brand-name">LogMind</span>
          <span className="brand-tag">Incident Intelligence</span>
        </div>

        <div className="header-center">
          {activeSession && (
            <span className="header-session-label" title={activeSession.name}>
              {activeSession.name}
            </span>
          )}
        </div>

        <div className="header-right">
          <div className={`status-pill ${statusDot.cls}`}>
            <span className="status-dot" />
            {statusDot.label}
          </div>
          {(rightResult || loading) && (
            <button
              className={`header-toggle-btn${rightOpen ? ' header-toggle-active' : ''}`}
              onClick={() => setRightOpen(o => !o)}
              title={rightOpen ? 'Hide analysis panel' : 'Show analysis panel'}
              id="btn-toggle-right"
            >⊞</button>
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="app-body">

        {/* Left: sessions + upload */}
        {leftOpen && (
          <LeftSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={selectSession}
            onNewSession={handleNewSession}
            onDeleteSession={handleDeleteSession}
            onFilesIngested={handleFilesIngested}
            backendOk={backendOk}
          />
        )}

        {/* Center: chat */}
        <main className="app-center" role="main">
          <ChatWindow
            messages={messages}
            loading={loading}
            activeSession={activeSession}
            onSend={handleSend}
            onViewTab={handleViewTab}
            disabled={!backendOk || !activeSessionId}
          />
        </main>

        {/* Right: analysis tabs */}
        {(rightOpen || loading) && (
          <RightSidebar
            open={rightOpen || loading}
            activeTab={rightTab}
            onTabChange={setRightTab}
            result={rightResult}
            graphData={graphData}
            onClose={() => setRightOpen(false)}
            loading={loading}
          />
        )}
      </div>

      {/* ── Toasts ── */}
      <ToastContainer
        toasts={toasts}
        onDismiss={id => setToasts(prev => prev.filter(t => t.id !== id))}
      />
    </div>
  )
}
