/**
 * App.jsx — Root application shell.
 *
 * Layout:
 *   [SessionSidebar | ChatPane | ArtifactPane (conditional)]
 *
 * State owned here:
 *   - sessions list + active session
 *   - messages for active session
 *   - LLM provider config
 *   - active artifact (opens artifact pane)
 *   - thinking/loading states
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { AlertCircle, Wifi, WifiOff } from 'lucide-react';

import SessionSidebar from './components/SessionSidebar';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ArtifactPane from './components/ArtifactPane';
import ProviderToggle from './components/ProviderToggle';
import ThinkingDots from './components/ThinkingDots';

import {
  createSession,
  listSessions,
  getMessages,
  sendChat,
  getLLMConfig,
  setLLMProvider,
  getHealth,
} from './api';

// ── Empty states ───────────────────────────────────────────────────────────────
function EmptyChat({ onSuggestion }) {
  const suggestions = [
    { label: 'Q&A',     text: 'What did Brian Chesky say about building culture?' },
    { label: 'Q&A',     text: 'How do the best growth teams measure success?' },
    { label: 'Essay',   text: 'Write a Ship30for30 essay on product-market fit' },
    { label: 'Artifact',text: 'Create an HTML dashboard of growth frameworks' },
  ];
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-8 py-16 text-center">
      <div className="w-14 h-14 rounded-2xl bg-accent-primary/10 border border-accent-primary/25 flex items-center justify-center mb-5">
        <span className="text-2xl font-black text-accent-primary">L</span>
      </div>
      <h2 className="text-xl font-bold text-text-primary mb-2">Lenny's Growth Assistant</h2>
      <p className="text-sm text-text-secondary max-w-sm mb-8 leading-relaxed">
        Ask product &amp; growth questions grounded in Lenny's Podcast, generate
        essays, or build interactive artifacts.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(s.text)}
            className="text-left px-4 py-3 rounded-xl border border-border bg-bg-surface
                       hover:border-accent-primary/40 hover:bg-bg-elevated transition-all duration-150 group"
          >
            <span className={`text-[10px] font-medium mb-1 block
              ${s.label === 'Q&A' ? 'text-skill-qa' : s.label === 'Essay' ? 'text-skill-ship30' : 'text-skill-artifact'}`}>
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

// ── Health status dot ─────────────────────────────────────────────────────────
function StatusDot({ healthy }) {
  return (
    <div className="flex items-center gap-1.5" title={healthy ? 'All systems operational' : 'Service issue detected'}>
      {healthy
        ? <Wifi className="w-3.5 h-3.5 text-skill-artifact" />
        : <WifiOff className="w-3.5 h-3.5 text-red-400" />
      }
      <span className={`text-[10px] font-medium ${healthy ? 'text-skill-artifact' : 'text-red-400'}`}>
        {healthy ? 'Live' : 'Degraded'}
      </span>
    </div>
  );
}

// ── Error banner ──────────────────────────────────────────────────────────────
function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 bg-red-950/60 border-b border-red-800/40 text-red-300 text-xs animate-fade-in">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="text-red-400 hover:text-red-200 font-medium">✕</button>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [artifact, setArtifact] = useState(null);
  const [provider, setProvider] = useState('ollama');
  const [modelName, setModelName] = useState('llama3.2');
  const [healthy, setHealthy] = useState(true);
  const [error, setError] = useState('');

  const bottomRef = useRef(null);

  // ── Scroll to bottom on new messages ───────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  // ── Load sessions on mount ─────────────────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        const [sessionData, config, health] = await Promise.all([
          listSessions(),
          getLLMConfig(),
          getHealth(),
        ]);
        setSessions(sessionData);
        setProvider(config.llm_provider);
        setModelName(
          config.llm_provider === 'anthropic'
            ? config.anthropic_model
            : config.ollama_chat_model
        );
        setHealthy(health.status === 'ok');
      } catch (e) {
        setError('Cannot reach backend. Make sure uvicorn is running on port 8000.');
        setHealthy(false);
      } finally {
        setSessionsLoading(false);
      }
    }
    init();
  }, []);

  // ── Load messages when session changes ─────────────────────────────────────
  useEffect(() => {
    if (!activeSessionId) { setMessages([]); return; }
    setMessagesLoading(true);
    getMessages(activeSessionId)
      .then(setMessages)
      .catch(() => setError('Failed to load messages.'))
      .finally(() => setMessagesLoading(false));
  }, [activeSessionId]);

  // ── Create new session ─────────────────────────────────────────────────────
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

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = useCallback(async (text) => {
    // Create session on first message if none active
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

    // Optimistic user message
    const userMsg = { id: Date.now(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setThinking(true);
    setError('');

    try {
      const data = await sendChat(sessionId, text);

      // Update session title after first message
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId ? { ...s, title: text.slice(0, 60) } : s
        )
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

      // Auto-open artifact pane
      if (data.artifact) {
        setArtifact(data.artifact);
      }
    } catch (e) {
      setError(`Failed to get response: ${e.message}`);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: '⚠️ Something went wrong. Check that the backend is running and your API keys are set.',
          skillUsed: null,
          sources: [],
          artifact: null,
        },
      ]);
    } finally {
      setThinking(false);
    }
  }, [activeSessionId, provider]);

  // ── Switch LLM provider ────────────────────────────────────────────────────
  const handleProviderChange = useCallback(async (newProvider) => {
    setProvider(newProvider);
    try {
      const config = await setLLMProvider(newProvider);
      setModelName(
        newProvider === 'anthropic' ? config.anthropic_model : config.ollama_chat_model
      );
    } catch {
      setError('Failed to switch LLM provider.');
      setProvider(provider); // revert
    }
  }, [provider]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-border bg-bg-surface flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-accent-primary flex items-center justify-center">
            <span className="text-white font-black text-sm">L</span>
          </div>
          <div>
            <h1 className="text-sm font-bold text-text-primary leading-none">Lenny's Growth Assistant</h1>
            <p className="text-[10px] text-text-muted mt-0.5">Powered by Lenny's Podcast transcripts</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <StatusDot healthy={healthy} />
          <ProviderToggle
            provider={provider}
            onChange={handleProviderChange}
            modelName={modelName}
          />
        </div>
      </header>

      {/* ── Error banner ────────────────────────────────────────────────────── */}
      <ErrorBanner message={error} onDismiss={() => setError('')} />

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={(id) => { setActiveSessionId(id); setArtifact(null); }}
          onNewChat={handleNewChat}
          loading={sessionsLoading}
        />

        {/* Chat pane */}
        <main className="flex flex-col flex-1 min-w-0 min-h-0">
          {/* Messages area */}
          <div className="flex-1 overflow-y-auto">
            {messagesLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="w-5 h-5 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin" />
              </div>
            )}

            {!messagesLoading && messages.length === 0 && (
              <EmptyChat onSuggestion={handleSend} />
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
            <div ref={bottomRef} className="h-4" />
          </div>

          {/* Input */}
          <ChatInput
            onSend={handleSend}
            disabled={thinking}
            placeholder="Ask about growth strategy, request an essay, or build an artifact…"
          />
        </main>

        {/* Artifact pane (conditional) */}
        {artifact && (
          <div className="w-[420px] flex-shrink-0 min-h-0 overflow-hidden">
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
