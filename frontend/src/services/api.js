/**
 * LogMind – API service layer
 * All backend calls go through this module.
 * Phase 0: stubs that will be fleshed out in Phase 3.
 */

import axios from 'axios'

// In development, Vite proxies /api → http://localhost:8000
// In Docker, nginx proxies /api → http://backend:8000
const BASE_URL = '/api'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,   // 60s – LLM responses can be slow
})

// ── Health ──────────────────────────────────────────────────────────────────
export async function checkHealth() {
  const { data } = await client.get('/health')
  return data
}

// ── Ingest ──────────────────────────────────────────────────────────────────
/**
 * @param {File[]} files
 * @returns {Promise<{status, files_processed, chunks_indexed, graph_nodes, graph_edges}>}
 */
export async function ingestFiles(files) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const { data } = await client.post('/ingest', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── Query ───────────────────────────────────────────────────────────────────
/**
 * @param {string} question
 * @returns {Promise<QueryResponse>}
 */
export async function queryIncident(question) {
  const { data } = await client.post('/query', { query: question })
  return data
}

// ── Graph ───────────────────────────────────────────────────────────────────
/**
 * @returns {Promise<{nodes: object[], edges: object[]}>}
 */
export async function getGraph() {
  const { data } = await client.get('/graph')
  return data
}
