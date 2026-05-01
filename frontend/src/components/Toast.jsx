/**
 * Toast – lightweight notification system
 * Usage: <ToastContainer toasts={toasts} onDismiss={id => ...} />
 * Trigger: addToast(setToasts, {type:'error', message:'...'})
 */
import './Toast.css'

export function addToast(setToasts, { type = 'info', message, duration = 4000 }) {
  const id = Date.now() + Math.random()
  setToasts(prev => [...prev, { id, type, message }])
  setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration)
}

const ICONS = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' }

export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null
  return (
    <div className="toast-container" role="region" aria-label="Notifications">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span className="toast-icon">{ICONS[t.type] || 'ℹ'}</span>
          <span className="toast-msg">{t.message}</span>
          <button className="toast-close" onClick={() => onDismiss(t.id)} aria-label="Dismiss">✕</button>
        </div>
      ))}
    </div>
  )
}
