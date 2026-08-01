/**
 * SessionSidebar.jsx — Nothing-style slim sidebar.
 * 3-dot menu per session: Rename (inline) + Delete (permanent).
 */
import { useState, useRef, useEffect } from 'react';
import { Plus, MessageSquare, MoreHorizontal, Pencil, Trash2, Check, X } from 'lucide-react';

function timeAgo(dateStr) {
  const now  = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60)     return 'just now';
  if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return 'Yesterday';
  return `${Math.floor(diff / 86400)}d ago`;
}

function groupSessions(sessions) {
  const now = new Date();
  const groups = { Today: [], Yesterday: [], Older: [] };
  sessions.forEach((s) => {
    const d = Math.floor((now - new Date(s.created_at)) / 86400000);
    if (d === 0) groups.Today.push(s);
    else if (d === 1) groups.Yesterday.push(s);
    else groups.Older.push(s);
  });
  return groups;
}

// ── Per-session row with 3-dot menu ──────────────────────────────────────────
function SessionRow({ session, isActive, onSelect, onDelete, onRename }) {
  const [menuOpen, setMenuOpen]       = useState(false);
  const [renaming, setRenaming]       = useState(false);
  const [renameValue, setRenameValue] = useState(session.title);
  const [displayTitle, setDisplayTitle] = useState(session.title);
  const prevTitleRef = useRef(session.title);
  const inputRef = useRef(null);
  const menuRef  = useRef(null);

  // Typewriter effect: triggers when title changes from "New chat" → real title
  useEffect(() => {
    const prev = prevTitleRef.current;
    const next = session.title;
    prevTitleRef.current = next;
    setRenameValue(next);

    // Guard: if next is empty, show "New chat" as safe fallback
    if (!next || !next.trim()) {
      setDisplayTitle('New chat');
      return;
    }

    if (prev === 'New chat' && next !== 'New chat') {
      // Animate: reveal one character at a time
      let i = 0;
      setDisplayTitle('');
      const id = setInterval(() => {
        i += 1;
        setDisplayTitle(next.slice(0, i));
        if (i >= next.length) clearInterval(id);
      }, 35);
      return () => clearInterval(id);
    } else {
      setDisplayTitle(next);
    }
  }, [session.title]);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  // Focus input when rename starts
  useEffect(() => {
    if (renaming) inputRef.current?.focus();
  }, [renaming]);

  const handleRenameSubmit = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== session.title) {
      onRename(session.id, trimmed);
    }
    setRenaming(false);
  };

  const handleRenameKey = (e) => {
    if (e.key === 'Enter') handleRenameSubmit();
    if (e.key === 'Escape') { setRenameValue(session.title); setRenaming(false); }
  };

  return (
    <div className="relative group">
      {/* Active indicator */}
      {isActive && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-white rounded-full" />
      )}

      {renaming ? (
        /* Inline rename input */
        <div className="flex items-center gap-1 pl-3 pr-1 py-1.5">
          <input
            ref={inputRef}
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={handleRenameKey}
            className="flex-1 bg-bg-elevated border border-white/20 rounded px-2 py-0.5
                       text-xs text-text-primary outline-none min-w-0"
          />
          <button onClick={handleRenameSubmit} className="p-1 text-skill-artifact hover:opacity-80">
            <Check className="w-3 h-3" />
          </button>
          <button onClick={() => { setRenameValue(displayTitle); setRenaming(false); }}
                  className="p-1 text-text-muted hover:text-text-secondary">
            <X className="w-3 h-3" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => onSelect(session.id)}
          className={`w-full text-left pl-3 pr-8 py-2 rounded-lg transition-all duration-100 ${
            isActive
              ? 'bg-bg-elevated text-text-primary'
              : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
          }`}
          title={session.title}
        >
          <p className="text-xs font-medium truncate leading-snug">{displayTitle}</p>
          <p className="text-[10px] text-text-muted mt-0.5">{timeAgo(session.created_at)}</p>
        </button>
      )}

      {/* 3-dot menu button */}
      {!renaming && (
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen(o => !o); }}
          className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded-md
                     text-text-muted opacity-0 group-hover:opacity-100
                     hover:text-text-secondary hover:bg-bg-elevated
                     transition-all duration-100"
          title="Options"
        >
          <MoreHorizontal className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Dropdown menu */}
      {menuOpen && (
        <div
          ref={menuRef}
          className="absolute right-0 top-full mt-1 z-50 bg-bg-elevated border border-border
                     rounded-lg shadow-xl shadow-black/40 py-1 w-36 animate-fade-in"
        >
          <button
            onClick={() => { setMenuOpen(false); setRenaming(true); }}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-text-secondary
                       hover:bg-bg-surface hover:text-text-primary transition-colors"
          >
            <Pencil className="w-3 h-3" /> Rename
          </button>
          <button
            onClick={() => { setMenuOpen(false); onDelete(session.id); }}
            className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-red-400
                       hover:bg-red-950/30 transition-colors"
          >
            <Trash2 className="w-3 h-3" /> Delete
          </button>
        </div>
      )}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
export default function SessionSidebar({
  sessions, activeSessionId, onSelectSession,
  onNewChat, onDeleteSession, onRenameSession, loading,
}) {
  const groups = groupSessions(sessions);

  return (
    <aside className="flex flex-col w-[240px] flex-shrink-0 h-full bg-bg-surface border-r border-border-subtle overflow-hidden">

      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 pt-4 pb-3">
        <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center flex-shrink-0">
          <span className="text-black font-black text-[11px] leading-none">L</span>
        </div>
        <span className="text-sm font-semibold text-text-primary tracking-tight">Lenny</span>
      </div>

      {/* New Chat */}
      <div className="px-3 pb-3">
        <button
          id="new-chat-btn"
          onClick={onNewChat}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg border border-border
                     text-xs text-text-secondary font-medium
                     hover:border-white/20 hover:text-text-primary hover:bg-bg-elevated
                     transition-all duration-150 group"
        >
          <Plus className="w-3.5 h-3.5 group-hover:rotate-90 transition-transform duration-200" />
          New chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {loading ? (
          <div className="space-y-1.5 px-2 pt-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-9 rounded-lg bg-bg-elevated animate-pulse"
                   style={{ opacity: 1 - i * 0.2 }} />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-10 text-center">
            <MessageSquare className="w-5 h-5 text-text-muted mx-auto mb-2" />
            <p className="text-xs text-text-muted">No chats yet</p>
          </div>
        ) : (
          Object.entries(groups).map(([label, items]) =>
            items.length === 0 ? null : (
              <div key={label} className="mb-3">
                <p className="px-2 py-1 text-[10px] font-semibold text-text-muted uppercase tracking-widest">
                  {label}
                </p>
                <div className="space-y-0.5">
                  {items.map((s) => (
                    <SessionRow
                      key={s.id}
                      session={s}
                      isActive={s.id === activeSessionId}
                      onSelect={onSelectSession}
                      onDelete={onDeleteSession}
                      onRename={onRenameSession}
                    />
                  ))}
                </div>
              </div>
            )
          )
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <p className="text-[10px] text-text-muted text-center">180 episodes · 4,604 chunks</p>
      </div>
    </aside>
  );
}
