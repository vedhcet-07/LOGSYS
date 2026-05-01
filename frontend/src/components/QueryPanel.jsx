/**
 * QueryPanel – natural-language question input with example queries.
 */
import { useState } from 'react'
import './QueryPanel.css'

const EXAMPLES = [
  'Why did auth-service fail around 2:31 AM?',
  'Summarize the main errors and anomalies in the logs.',
  'Is the latency spike related to the database timeout?',
]

export default function QueryPanel({ onResult, disabled }) {
  const [query, setQuery]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [elapsed, setElapsed]   = useState(null)

  const handleSubmit = async (q) => {
    const text = (q || query).trim()
    if (!text) return
    setLoading(true)
    setError(null)
    setElapsed(null)
    const t0 = Date.now()
    try {
      const { queryIncident } = await import('../services/api')
      const data = await queryIncident(text)
      setElapsed(((Date.now() - t0) / 1000).toFixed(1))
      onResult?.(data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const useExample = (ex) => {
    setQuery(ex)
    handleSubmit(ex)
  }

  return (
    <section className="query-panel card" aria-label="Query Panel">
      <div className="panel-header">
        <h3>Ask the Incident Assistant</h3>
        {elapsed && (
          <span className="text-subtle" style={{ fontSize: '0.75rem' }}>
            ⏱ {elapsed}s
          </span>
        )}
      </div>

      <textarea
        id="query-input"
        className="input query-textarea"
        placeholder="e.g. Why did auth-service fail at 2:31 AM?"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
        }}
        rows={3}
        disabled={disabled || loading}
        aria-label="Incident question"
      />

      <button
        id="query-btn"
        className="btn btn-primary w-full"
        onClick={() => handleSubmit()}
        disabled={!query.trim() || loading || disabled}
      >
        {loading ? (
          <><span className="spinner" />&nbsp;Agents are thinking…</>
        ) : (
          <>🔎 Analyze Incident</>
        )}
      </button>

      {/* Example queries */}
      <div className="examples">
        <p className="examples-label">Try an example:</p>
        <div className="examples-list">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              className="example-chip"
              onClick={() => useExample(ex)}
              disabled={loading || disabled}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="query-error fade-in">
          <p className="text-danger">✗ {error}</p>
        </div>
      )}
    </section>
  )
}
