/**
 * SessionSidebar.jsx — Nothing-style slim sidebar.
 * 240px wide, white-border active indicator, relative timestamps,
 * hover-to-delete session.
 */
import { useState } from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';

function timeAgo(dateStr) {
  const now  = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60)    return 'just now';
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return 'Yesterday';
  return `${Math.floor(diff / 86400)}d ago`;
}

function groupSessions(sessions) {
  const now = new Date();
  const groups = { Today: [], Yesterday: [], Older: [] };
  sessions.forEach((s) => {
    const d = Math.floor((now - new Date(s.created_at || Date.now())) / 86400000);
    if (d === 0) groups.Today.push(s);
    else if (d === 1) groups.Yesterday.push(s);
    else groups.Older.push(s);
  });
  return groups;
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  loading,
}) {
  const [hoveredId, setHoveredId] = useState(null);
  const groups = groupSessions(sessions);

  return (
    <aside className="flex flex-col w-[240px] flex-shrink-0 h-full bg-bg-surface border-r border-border-subtle overflow-hidden">

      {/* ── Brand ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2.5 px-4 pt-4 pb-3">
        <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center flex-shrink-0">
          <span className="text-black font-black text-[11px] leading-none">L</span>
        </div>
        <span className="text-sm font-semibold text-text-primary tracking-tight">Lenny</span>
      </div>

      {/* ── New Chat ──────────────────────────────────────────────────────── */}
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

      {/* ── Session list ──────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {loading ? (
          <div className="space-y-1.5 px-2 pt-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-9 rounded-lg bg-bg-elevated animate-pulse" style={{ opacity: 1 - i * 0.2 }} />
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
                  {items.map((s) => {
                    const isActive = s.id === activeSessionId;
                    const isHovered = hoveredId === s.id;
                    return (
                      <div
                        key={s.id}
                        className="relative group"
                        onMouseEnter={() => setHoveredId(s.id)}
                        onMouseLeave={() => setHoveredId(null)}
                      >
                        {/* Active left-border indicator */}
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-white rounded-full" />
                        )}
                        <button
                          onClick={() => onSelectSession(s.id)}
                          className={`w-full text-left pl-3 pr-8 py-2 rounded-lg transition-all duration-100 ${
                            isActive
                              ? 'bg-bg-elevated text-text-primary'
                              : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
                          }`}
                          title={s.title || 'New chat'}
                        >
                          <p className="text-xs font-medium truncate leading-snug">
                            {s.title || 'New chat'}
                          </p>
                          <p className="text-[10px] text-text-muted mt-0.5">
                            {timeAgo(s.created_at)}
                          </p>
                        </button>
                        {/* Delete on hover */}
                        {isHovered && onDeleteSession && (
                          <button
                            onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}
                            className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md
                                       text-text-muted hover:text-red-400 hover:bg-red-950/30
                                       transition-all duration-100"
                            title="Delete chat"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )
          )
        )}
      </div>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <p className="text-[10px] text-text-muted text-center">
          180 episodes · 4,604 chunks
        </p>
      </div>
    </aside>
  );
}
