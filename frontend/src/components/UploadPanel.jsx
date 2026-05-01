/**
 * UploadPanel – drag-and-drop multi-modal file upload with ingest trigger.
 */
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import './UploadPanel.css'

const ACCEPTED = {
  'text/plain':        ['.log', '.txt'],
  'image/png':         ['.png'],
  'image/jpeg':        ['.jpg', '.jpeg'],
  'application/json':  ['.json'],
  'text/csv':          ['.csv'],
}

function getModality(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  if (['log', 'txt'].includes(ext))  return 'log'
  if (['png', 'jpg', 'jpeg'].includes(ext)) return 'image'
  if (['csv', 'json'].includes(ext)) return 'metrics'
  return 'other'
}

const MOD_ICONS  = { log: '📄', metrics: '📊', image: '🖼️', other: '📎' }
const MOD_BADGE  = { log: 'badge-log', metrics: 'badge-metrics', image: 'badge-image', other: '' }

export default function UploadPanel({ onIngestDone, onFilesChanged }) {
  const [files, setFiles]         = useState([])
  const [ingesting, setIngesting] = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState(null)

  const onDrop = useCallback((accepted) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      const fresh    = accepted.filter(f => !existing.has(f.name))
      const next     = [...prev, ...fresh]
      onFilesChanged?.(next)
      return next
    })
    setResult(null)
    setError(null)
  }, [onFilesChanged])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: true,
  })

  const removeFile = (name) => {
    setFiles(prev => {
      const next = prev.filter(f => f.name !== name)
      onFilesChanged?.(next)
      return next
    })
  }

  const handleIngest = async () => {
    if (!files.length) return
    setIngesting(true)
    setError(null)
    setResult(null)
    try {
      const { ingestFiles } = await import('../services/api')
      const data = await ingestFiles(files)
      setResult(data)
      onIngestDone?.(data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Ingest failed')
    } finally {
      setIngesting(false)
    }
  }

  const modCounts = files.reduce((acc, f) => {
    const m = getModality(f.name)
    acc[m] = (acc[m] || 0) + 1
    return acc
  }, {})

  return (
    <section className="upload-panel card" aria-label="File Upload">
      <div className="panel-header">
        <h3>Upload Files</h3>
        <div className="mod-summary">
          {Object.entries(modCounts).map(([m, n]) => (
            <span key={m} className={`badge ${MOD_BADGE[m]}`}>
              {MOD_ICONS[m]} {n}
            </span>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`dropzone${isDragActive ? ' dropzone--active' : ''}`}
        role="button"
        aria-label="Drop files here or click to browse"
      >
        <input {...getInputProps()} />
        <div className="dropzone-icon">{isDragActive ? '📂' : '☁️'}</div>
        <p className="dropzone-text">
          {isDragActive
            ? 'Drop to add files…'
            : 'Drag & drop logs, images, metrics'}
        </p>
        <p className="dropzone-hint">.log .txt .png .jpg .json .csv</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <ul className="file-list">
          {files.map((f) => {
            const m = getModality(f.name)
            return (
              <li key={f.name} className="file-item fade-in">
                <span>{MOD_ICONS[m]}</span>
                <span className={`badge ${MOD_BADGE[m]}`}>{m}</span>
                <span className="file-name mono">{f.name}</span>
                <span className="file-size text-subtle">
                  {(f.size / 1024).toFixed(1)} KB
                </span>
                <button
                  className="file-remove"
                  onClick={() => removeFile(f.name)}
                  title="Remove"
                  aria-label={`Remove ${f.name}`}
                >
                  ✕
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {/* Ingest button */}
      <button
        id="ingest-btn"
        className="btn btn-primary w-full"
        onClick={handleIngest}
        disabled={!files.length || ingesting}
      >
        {ingesting ? (
          <><span className="spinner" />&nbsp;Ingesting…</>
        ) : (
          <>⚡ Ingest {files.length} file{files.length !== 1 ? 's' : ''}</>
        )}
      </button>

      {/* Result */}
      {result && (
        <div className="ingest-result fade-in">
          <div className="result-row">
            <span className="text-success">✓ {result.status}</span>
            <span className="text-subtle">{result.files_processed} files</span>
          </div>
          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-val">{result.chunks_indexed}</span>
              <span className="stat-lbl">vectors</span>
            </div>
            <div className="stat-item">
              <span className="stat-val">{result.graph_nodes}</span>
              <span className="stat-lbl">nodes</span>
            </div>
            <div className="stat-item">
              <span className="stat-val">{result.graph_edges}</span>
              <span className="stat-lbl">edges</span>
            </div>
          </div>
          {result.errors?.length > 0 && (
            <div className="result-errors">
              {result.errors.map((e, i) => <p key={i} className="text-warning">⚠ {e}</p>)}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="ingest-error fade-in">
          <p className="text-danger">✗ {error}</p>
        </div>
      )}
    </section>
  )
}
