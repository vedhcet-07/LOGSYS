/**
 * LogMind – API service layer (Phase 4B: session-aware)
 */
import axios from 'axios'

// In Docker (nginx): calls go to /api and nginx proxies to backend
// On Render Static Site: VITE_BACKEND_URL is set at build time to the backend URL
const BASE_URL = import.meta.env.VITE_BACKEND_URL
  ? `${import.meta.env.VITE_BACKEND_URL}/api`
  : '/api'

const client = axios.create({ baseURL: BASE_URL, timeout: 120_000 })

// ── Health ────────────────────────────────────────────────────────────────────
export const checkHealth = async () => (await client.get('/health')).data

// ── Sessions ──────────────────────────────────────────────────────────────────
export const createSession  = async (name) => (await client.post('/sessions', { name })).data
export const listSessions   = async ()       => (await client.get('/sessions')).data
export const getSession     = async (id)     => (await client.get(`/sessions/${id}`)).data
export const deleteSession  = async (id)     => (await client.delete(`/sessions/${id}`)).data

// ── Session — Ingest ──────────────────────────────────────────────────────────
export async function sessionIngest(sessionId, files) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const { data } = await client.post(`/sessions/${sessionId}/ingest`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  })
  return data
}

// ── Session — Query ───────────────────────────────────────────────────────────
export async function sessionQuery(sessionId, query) {
  const { data } = await client.post(`/sessions/${sessionId}/query`, { query }, {
    timeout: 120_000,
  })
  return data
}

// ── Session — Graph ───────────────────────────────────────────────────────────
export const sessionGraph   = async (id) => (await client.get(`/sessions/${id}/graph`)).data

// ── Session — Chat history ────────────────────────────────────────────────────
export const sessionChat    = async (id) => (await client.get(`/sessions/${id}/chat`)).data
export const clearChat      = async (id) => (await client.delete(`/sessions/${id}/chat`)).data

// ── Global (backward-compat) ──────────────────────────────────────────────────
export async function ingestFiles(files) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return (await client.post('/ingest', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const queryIncident = async (q) => (await client.post('/query', { query: q })).data
export const getGraph      = async ()  => (await client.get('/graph')).data
