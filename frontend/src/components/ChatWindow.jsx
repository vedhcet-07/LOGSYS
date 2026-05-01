/**
 * ChatWindow – center chat feed + sticky input bar
 */
import { useEffect, useRef, useState } from 'react'
import ChatMessage from './ChatMessage'
import './ChatWindow.css'

const CHIPS = [
  'Why did auth-service fail at 2:31 AM?',
  'What caused the database connection pool exhaustion?',
  'Analyze the latency spike in payment-service',
  'Which services were affected by the memory leak?',
]

export default function ChatWindow({
  messages,
  loading,
  activeSession,
  onSend,
  onViewTab,
  disabled,
}) {
  const [input,   setInput]   = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px'
  }, [input])

  const handleSend = () => {
    const q = input.trim()
    if (!q || loading || disabled) return
    onSend(q)
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const showEmpty = messages.length === 0 && !loading

  return (
    <div className="chat-window">
      {/* Message feed */}
      <div className="chat-feed" id="chat-feed">
        {showEmpty ? (
          <div className="chat-empty">
            <div className="ce-logo">🧠</div>
            <h2 className="ce-title">LogMind</h2>
            <p className="ce-subtitle">
              {activeSession
                ? `Session: ${activeSession.name}`
                : 'Multi-Modal Graph RAG Incident Assistant'}
            </p>
            {activeSession ? (
              <p className="ce-hint">
                {activeSession.node_count > 0
                  ? `${activeSession.node_count} graph nodes ready — ask about your logs`
                  : 'Upload files to the session, then ask a question'}
              </p>
            ) : (
              <p className="ce-hint">Select or create a session to begin</p>
            )}
            {/* Example chips */}
            <div className="ce-chips">
              {CHIPS.map((q, i) => (
                <button
                  key={i}
                  className="ce-chip"
                  onClick={() => { setInput(q); textareaRef.current?.focus() }}
                  disabled={disabled}
                  id={`chip-example-${i}`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map(msg => (
              <ChatMessage key={msg.id} message={msg} onViewTab={onViewTab} />
            ))}
            {loading && (
              <ChatMessage message={{ id: 'thinking', role: 'thinking' }} onViewTab={() => {}} />
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Sticky input bar */}
      <div className="chat-input-bar">
        <div className={`chat-input-wrap${disabled ? ' chat-input-disabled' : ''}`}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder={
              !activeSession
                ? 'Select a session first…'
                : disabled
                  ? 'Backend offline…'
                  : 'Ask about your incident…'
            }
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            rows={1}
            id="chat-input"
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={disabled || loading || !input.trim()}
            id="btn-send"
            aria-label="Send"
          >
            {loading ? (
              <div className="spinner" style={{ width: 18, height: 18 }} />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
        <div className="chat-input-hint">
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
