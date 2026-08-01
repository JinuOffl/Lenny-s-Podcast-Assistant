/**
 * api.js — Thin wrapper around the FastAPI backend.
 * All fetch calls go through here so the base URL is configured in one place.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Sessions ──────────────────────────────────────────────────────────────────
export const createSession = (title = 'New chat', llm_provider = 'ollama') =>
  request('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, llm_provider }),
  });

export const listSessions = () => request('/sessions');

// ── Messages ──────────────────────────────────────────────────────────────────
export const getMessages = (sessionId) =>
  request(`/sessions/${sessionId}/messages`);

// ── Chat ──────────────────────────────────────────────────────────────────────
export const sendChat = (sessionId, message) =>
  request(`/sessions/${sessionId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });

// ── Config ────────────────────────────────────────────────────────────────────
export const getLLMConfig = () => request('/config/llm');

export const setLLMProvider = (llm_provider) =>
  request('/config/llm', {
    method: 'POST',
    body: JSON.stringify({ llm_provider }),
  });

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => request('/health');
