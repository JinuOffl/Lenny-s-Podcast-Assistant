/**
 * App.jsx — Root application shell.
 *
 * Layout:
 *   [SessionSidebar 240px | Chat pane (centered 760px) | ArtifactPane (conditional)]
 *
 * Header: 44px slim topbar — status dot + provider toggle only
 * Empty state: centered ChatGPT-style with suggestion chips
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { WifiOff, Wifi, AlertCircle } from 'lucide-react';

import SessionSidebar   from './components/SessionSidebar';
import ChatMessage      from './components/ChatMessage';
import ChatInput        from './components/ChatInput';
import ArtifactPane     from './components/ArtifactPane';
import ProviderToggle   from './components/ProviderToggle';
import ThinkingDots     from './components/ThinkingDots';

import {
  createSession, listSessions, getMessages,
  sendChat, getLLMConfig, setLLMProvider, getHealth,
} from './api';

// ── Suggestion chips ──────────────────────────────────────────────────────────
const SUGGESTIONS = [
  { label: 'Q&A',      text: 'What did Brian Chesky say about company culture?' },
  { label: 'Q&A',      text: 'How do the best growth teams measure success?' },
  { label: 'Essay',    text: 'Write a Ship30for30 essay on product-market fit' },
  { label: 'Artifact', text: 'Create an HTML dashboard of growth frameworks' },
];

function EmptyState({ onSuggestion }) {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 pb-16">
      {/* Monogram */}
      <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center mb-6 shadow-lg shadow-black/40">
        <span className="text-black font-black text-lg leading-none">L</span>
      </div>
      <h2 className="text-xl font-semibold text-text-primary mb-1">
        How can I help you today?
      </h2>
      <p className="text-sm text-text-muted mb-8 text-center max-w-sm">
        Ask product &amp; growth questions, write essays, or build interactive artifacts.
      </p>
      {/* Suggestion grid */}
      <div className="grid grid-cols-2 gap-2 w-full max-w-[520px]">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(s.text)}
            className="text-left px-3.5 py-2.5 rounded-xl border border-border bg-bg-surface
                       hover:border-white/15 hover:bg-bg-elevated
                       transition-all duration-150 group"
          >
            <span className={`text-[9px] font-semibold uppercase tracking-widest block mb-1 ${
              s.label === 'Q&A' ? 'text-skill-qa' : s.label === 'Essay' ? 'text-skill-ship30' : 'text-skill-artifact'
            }`}>
              {s.label}
            </span>
            <p className="text-xs text-text-secondary group-hover:text-text-primary transition-colors leading-snug">
              {s.text}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Status dot ────────────────────────────────────────────────────────────────
function StatusDot({ healthy }) {
  return (
    <div className="flex items-center gap-1.5" title={healthy ? 'All systems operational' : 'Backend issue'}>
      {healthy
        ? <span className="w-1.5 h-1.5 rounded-full bg-skill-artifact" />
        : <WifiOff className="w-3.5 h-3.5 text-red-400" />
      }
      <span className={`text-[10px] font-medium ${healthy ? 'text-text-muted' : 'text-red-400'}`}>
        {healthy ? 'Live' : 'Offline'}
      </span>
    </div>
  );
}

// ── Error toast ───────────────────────────────────────────────────────────────
function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-950/50 border-b border-red-900/40 text-red-300 text-xs">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="text-red-400 hover:text-red-200 font-bold leading-none">×</button>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [sessions, setSessions]             = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages]             = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [thinking, setThinking]             = useState(false);
  const [artifact, setArtifact]             = useState(null);
  const [provider, setProvider]             = useState('ollama');
  const [modelName, setModelName]           = useState('llama3.2');
  const [healthy, setHealthy]               = useState(true);
  const [error, setError]                   = useState('');

  const bottomRef = useRef(null);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  // Load on mount
  useEffect(() => {
    async function init() {
      try {
        const [sessionData, config, health] = await Promise.all([
          listSessions(), getLLMConfig(), getHealth(),
        ]);
        setSessions(sessionData);
        setProvider(config.llm_provider);
        setModelName(
          config.llm_provider === 'anthropic'
            ? config.anthropic_model
            : config.ollama_chat_model
        );
        setHealthy(health.status === 'ok');
      } catch {
        setError('Cannot reach backend. Make sure uvicorn is running on port 8000.');
        setHealthy(false);
      } finally {
        setSessionsLoading(false);
      }
    }
    init();
  }, []);

  // Load messages for active session
  useEffect(() => {
    if (!activeSessionId) { setMessages([]); return; }
    setMessagesLoading(true);
    getMessages(activeSessionId)
      .then(setMessages)
      .catch(() => setError('Failed to load messages.'))
      .finally(() => setMessagesLoading(false));
  }, [activeSessionId]);

  // New chat
  const handleNewChat = useCallback(async () => {
    try {
      const session = await createSession('New chat', provider);
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setArtifact(null);
    } catch {
      setError('Failed to create session.');
    }
  }, [provider]);

  // Delete session
  const handleDeleteSession = useCallback(async (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSessionId === id) {
      setActiveSessionId(null);
      setMessages([]);
      setArtifact(null);
    }
    // Note: add DELETE /sessions/:id to api.js if backend supports it
  }, [activeSessionId]);

  // Send message
  const handleSend = useCallback(async (text) => {
    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createSession('New chat', provider);
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(session.id);
        sessionId = session.id;
      } catch {
        setError('Failed to create session.');
        return;
      }
    }

    const userMsg = { id: Date.now(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setThinking(true);
    setError('');

    try {
      const data = await sendChat(sessionId, text);
      setSessions((prev) =>
        prev.map((s) => s.id === sessionId ? { ...s, title: text.slice(0, 60) } : s)
      );
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        skillUsed: data.skill_used,
        sources: data.sources || [],
        artifact: data.artifact || null,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (data.artifact) setArtifact(data.artifact);
    } catch (e) {
      setError(`Failed to get response: ${e.message}`);
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: '⚠️ Something went wrong. Check that the backend is running and your API keys are set.',
        skillUsed: null, sources: [], artifact: null,
      }]);
    } finally {
      setThinking(false);
    }
  }, [activeSessionId, provider]);

  // Switch provider
  const handleProviderChange = useCallback(async (newProvider) => {
    setProvider(newProvider);
    try {
      const config = await setLLMProvider(newProvider);
      setModelName(newProvider === 'anthropic' ? config.anthropic_model : config.ollama_chat_model);
    } catch {
      setError('Failed to switch LLM provider.');
      setProvider(provider);
    }
  }, [provider]);

  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">

      {/* ── Topbar (44px) ─────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 h-11 flex-shrink-0
                         border-b border-border-subtle bg-bg-surface z-10">
        <StatusDot healthy={healthy} />
        <ProviderToggle
          provider={provider}
          onChange={handleProviderChange}
          modelName={modelName}
        />
      </header>

      {/* ── Error banner ───────────────────────────────────────────────────── */}
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* Sidebar */}
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={(id) => { setActiveSessionId(id); setArtifact(null); }}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
          loading={sessionsLoading}
        />

        {/* Chat pane */}
        <main className="flex flex-col flex-1 min-w-0 min-h-0 bg-bg-base">

          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            {messagesLoading && (
              <div className="flex justify-center pt-12">
                <div className="w-4 h-4 border-2 border-border border-t-white/40 rounded-full animate-spin" />
              </div>
            )}

            {!messagesLoading && messages.length === 0 && (
              <EmptyState onSuggestion={handleSend} />
            )}

            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                skillUsed={msg.skill_used || msg.skillUsed}
                sources={msg.sources}
                artifact={msg.artifact}
                onOpenArtifact={setArtifact}
              />
            ))}

            {thinking && <ThinkingDots />}
            <div ref={bottomRef} className="h-6" />
          </div>

          {/* Composer */}
          <ChatInput
            onSend={handleSend}
            disabled={thinking}
            placeholder="Ask anything about growth…"
          />
        </main>

        {/* Artifact pane */}
        {artifact && (
          <div className="w-[420px] flex-shrink-0 min-h-0 overflow-hidden border-l border-border-subtle">
            <ArtifactPane
              artifact={artifact}
              onClose={() => setArtifact(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
