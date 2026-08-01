/**
 * App.jsx — Root application shell.
 * Phase 2 upgrade: streaming SSE, fixed first-message race, session rename/delete,
 * auto-title refresh, proper conversation memory.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { WifiOff, AlertCircle } from 'lucide-react';

import SessionSidebar   from './components/SessionSidebar';
import ChatMessage      from './components/ChatMessage';
import ChatInput        from './components/ChatInput';
import ArtifactPane     from './components/ArtifactPane';
import ProviderToggle   from './components/ProviderToggle';
import ThinkingDots     from './components/ThinkingDots';

import {
  createSession, listSessions, getMessages,
  streamChat, getLLMConfig, setLLMProvider, getHealth,
  renameSession, deleteSession,
} from './api';

// ── Suggestion chips ──────────────────────────────────────────────────────────
const SUGGESTIONS = [
  { label: 'Q&A',      text: 'What did Brian Chesky say about company culture?' },
  { label: 'Q&A',      text: 'How do the best growth teams measure success?' },
  { label: 'Essay',    text: 'Write a Ship30for30 essay on product-market fit' },
  { label: 'Artifact', text: 'Create an HTML line chart showing growth frameworks' },
];

function EmptyState({ onSuggestion }) {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 pb-20">
      <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center mb-6">
        <span className="text-black font-black text-lg leading-none">L</span>
      </div>
      <h2 className="text-xl font-semibold text-text-primary mb-1">How can I help you today?</h2>
      <p className="text-sm text-text-muted mb-8 text-center max-w-sm">
        Ask product &amp; growth questions, write essays, or build interactive artifacts.
      </p>
      <div className="grid grid-cols-2 gap-2 w-full max-w-[520px]">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(s.text)}
            className="text-left px-3.5 py-2.5 rounded-xl border border-border bg-bg-surface
                       hover:border-white/15 hover:bg-bg-elevated transition-all duration-150 group"
          >
            <span className={`text-[9px] font-semibold uppercase tracking-widest block mb-1 ${
              s.label === 'Q&A' ? 'text-skill-qa' : s.label === 'Essay' ? 'text-skill-ship30' : 'text-skill-artifact'
            }`}>{s.label}</span>
            <p className="text-xs text-text-secondary group-hover:text-text-primary transition-colors leading-snug">{s.text}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function StatusDot({ healthy }) {
  return (
    <div className="flex items-center gap-1.5">
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

function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-950/50 border-b border-red-900/40 text-red-300 text-xs">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="text-red-400 hover:text-red-200 font-bold">×</button>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [sessions, setSessions]               = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages]               = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [streaming, setStreaming]             = useState(false);
  const [artifact, setArtifact]               = useState(null);
  const [provider, setProvider]               = useState('ollama');
  const [modelName, setModelName]             = useState('qwen3:4b');
  const [healthy, setHealthy]                 = useState(true);
  const [error, setError]                     = useState('');

  const bottomRef    = useRef(null);
  const abortRef     = useRef(null); // stores current SSE AbortController

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  // ── Init ──
  useEffect(() => {
    async function init() {
      try {
        const [sessionData, config, health] = await Promise.all([
          listSessions(), getLLMConfig(), getHealth(),
        ]);
        setSessions(sessionData);
        setProvider(config.llm_provider);
        setModelName(config.llm_provider === 'anthropic' ? config.anthropic_model : config.ollama_chat_model);
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

  // ── Load messages ──
  useEffect(() => {
    if (!activeSessionId) { setMessages([]); return; }
    setMessagesLoading(true);
    getMessages(activeSessionId)
      .then(setMessages)
      .catch(() => setError('Failed to load messages.'))
      .finally(() => setMessagesLoading(false));
  }, [activeSessionId]);

  // ── New chat ──
  const handleNewChat = useCallback(async () => {
    try {
      const session = await createSession('New chat', provider);
      setSessions(prev => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setArtifact(null);
    } catch {
      setError('Failed to create session.');
    }
  }, [provider]);

  // ── Delete session ──
  const handleDeleteSession = useCallback(async (id) => {
    await deleteSession(id);
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      setActiveSessionId(null);
      setMessages([]);
      setArtifact(null);
    }
  }, [activeSessionId]);

  // ── Rename session ──
  const handleRenameSession = useCallback(async (id, newTitle) => {
    const updated = await renameSession(id, newTitle);
    setSessions(prev => prev.map(s => s.id === id ? { ...s, title: updated.title } : s));
  }, []);

  // ── Send message (streaming) ──
  const handleSend = useCallback(async (text) => {
    // Abort any existing stream
    abortRef.current?.abort();

    let sessionId = activeSessionId;

    // Create session if needed FIRST (fixes race condition)
    if (!sessionId) {
      try {
        const session = await createSession('New chat', provider);
        setSessions(prev => [session, ...prev]);
        setActiveSessionId(session.id);
        sessionId = session.id;
      } catch {
        setError('Failed to create session.');
        return;
      }
    }

    // Add user message to state
    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);

    // Add placeholder for assistant streaming response
    const assistantId = `a-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      skillUsed: null,
      sources: [],
      artifact: null,
      _streaming: true,
    }]);

    setStreaming(true);
    setError('');

    const ctrl = streamChat(sessionId, text, {
      onToken: (token) => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: m.content + token } : m
        ));
      },
      onDone: async (meta) => {
        // Finalize the streaming message with metadata
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, _streaming: false, skillUsed: meta.skill_used, sources: meta.sources || [], artifact: meta.artifact || null }
            : m
        ));
        if (meta.artifact) setArtifact(meta.artifact);

        // Refresh sessions to get updated smart title
        const freshSessions = await listSessions();
        setSessions(freshSessions);

        setStreaming(false);
      },
      onError: (err) => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, _streaming: false, content: `⚠️ ${err.message || 'Something went wrong.'}` }
            : m
        ));
        setStreaming(false);
        setError(err.message);
      },
    });

    abortRef.current = ctrl;
  }, [activeSessionId, provider]);

  // ── Switch provider ──
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

      {/* ── Topbar ──────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 h-11 flex-shrink-0
                         border-b border-border-subtle bg-bg-surface z-10">
        <StatusDot healthy={healthy} />
        <ProviderToggle provider={provider} onChange={handleProviderChange} modelName={modelName} />
      </header>

      <ErrorBanner message={error} onDismiss={() => setError('')} />

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={(id) => { setActiveSessionId(id); setArtifact(null); }}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
          loading={sessionsLoading}
        />

        {/* Chat pane */}
        <main className="flex flex-col flex-1 min-w-0 min-h-0 bg-bg-base">

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
                isStreaming={msg._streaming}
              />
            ))}

            {/* ThinkingDots: show only while streaming but BEFORE first token arrives */}
            {streaming && messages[messages.length - 1]?.content === '' && <ThinkingDots />}

            <div ref={bottomRef} className="h-6" />
          </div>

          <ChatInput
            onSend={handleSend}
            disabled={streaming}
            placeholder="Ask anything about growth…"
          />
        </main>

        {artifact && (
          <div className="w-[420px] flex-shrink-0 min-h-0 overflow-hidden border-l border-border-subtle">
            <ArtifactPane artifact={artifact} onClose={() => setArtifact(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
