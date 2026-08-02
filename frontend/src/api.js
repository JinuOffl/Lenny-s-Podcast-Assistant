/**
 * api.js — Thin wrapper around the FastAPI backend.
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
  request('/sessions', { method: 'POST', body: JSON.stringify({ title, llm_provider }) });

export const listSessions = () => request('/sessions');

export const renameSession = (sessionId, title) =>
  request(`/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify({ title }) });

export const deleteSession = (sessionId) =>
  fetch(`${BASE_URL}/sessions/${sessionId}`, { method: 'DELETE' });

// ── Messages ──────────────────────────────────────────────────────────────────
export const getMessages = (sessionId) => request(`/sessions/${sessionId}/messages`);

// ── Chat (blocking fallback) ──────────────────────────────────────────────────
export const sendChat = (sessionId, message) =>
  request(`/sessions/${sessionId}/chat`, { method: 'POST', body: JSON.stringify({ message }) });

/**
 * streamChat — Server-Sent Events streaming chat.
 * Calls onToken(str) for each text token, onDone(meta) when complete.
 * Returns an AbortController so caller can cancel.
 */
export function streamChat(sessionId, message, { onToken, onStep, onDone, onError }) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`API error ${res.status}: ${body}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE lines come as "data: {...}\n\n"
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete last line

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const raw = trimmed.slice(5).trim();
          if (!raw) continue;
          try {
            const event = JSON.parse(raw);
            if (event.error) { onError?.(new Error(event.error)); return; }
            if (event.done) { onDone?.(event); return; }
            if (event.step != null) { onStep?.(event.step); continue; }
            if (event.token != null) onToken?.(event.token);
          } catch { /* ignore malformed lines */ }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') onError?.(err);
    }
  })();

  return controller;
}

// ── Config ────────────────────────────────────────────────────────────────────
export const getLLMConfig = () => request('/config/llm');

export const setLLMProvider = (llm_provider) =>
  request('/config/llm', { method: 'POST', body: JSON.stringify({ llm_provider }) });

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => request('/health');

/**
 * streamResearchChat — Research Mode SSE streaming (5-agent pipeline).
 *
 * Identical fetch/ReadableStream pattern to streamChat(), but:
 *   1. Calls /sessions/{id}/chat/research/stream
 *   2. Handles {"agent": "...", "step": "..."} events → onStep({agent, step})
 *   3. Done event carries extra fields: confidence, healing_attempts,
 *      agent_steps, research_stats
 *
 * callbacks: { onToken, onStep, onDone, onError }
 *   onStep({agent, step}) — called for each agent status event
 *   onDone(meta)          — meta includes confidence, researchStats, etc.
 */
export function streamResearchChat(sessionId, message, { onToken, onStep, onDone, onError }) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat/research/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`API error ${res.status}: ${body}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const raw = trimmed.slice(5).trim();
          if (!raw) continue;
          try {
            const event = JSON.parse(raw);
            if (event.error)  { onError?.(new Error(event.error)); return; }
            if (event.done)   { onDone?.(event); return; }
            if (event.agent && event.step) { onStep?.({ agent: event.agent, step: event.step }); continue; }
            if (event.token != null) onToken?.(event.token);
          } catch { /* ignore malformed lines */ }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('[ResearchChat] Stream error:', err);
        onError?.(err);
      }
    }
  })();

  return controller;
}
