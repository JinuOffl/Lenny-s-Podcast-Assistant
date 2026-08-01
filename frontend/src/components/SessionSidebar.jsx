/**
 * SessionSidebar.jsx
 * ChatGPT-style session sidebar: thin, dark, "+ New Thread" at top.
 */
import { PlusIcon, MessageSquareIcon } from 'lucide-react';

function timeAgo(dateStr) {
  const now  = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60)   return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  loading,
}) {
  return (
    <aside className="flex flex-col w-[200px] flex-shrink-0 border-r border-border/50
                       bg-background overflow-hidden">

      {/* Logo row */}
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#f97316] to-[#fbbf24]
                        flex items-center justify-center flex-shrink-0">
          <span className="text-white font-black text-[10px]">L</span>
        </div>
        <span className="text-sm font-semibold text-foreground">assistant-ui</span>
      </div>

      {/* New Thread button */}
      <div className="px-2 pb-2">
        <button
          onClick={onNewChat}
          className="flex items-center gap-2 w-full px-3 py-1.5 rounded-lg
                     text-sm text-muted-foreground hover:bg-muted/60
                     transition-colors duration-150 group"
        >
          <PlusIcon className="w-4 h-4 flex-shrink-0 transition-transform
                                group-hover:rotate-90 duration-200" />
          <span>New Thread</span>
        </button>
      </div>

      {/* Divider */}
      <div className="h-px bg-border/50 mx-2 mb-2" />

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {loading ? (
          <div className="px-3 py-2 text-xs text-muted-foreground animate-pulse">
            Loading…
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-8 text-xs text-muted-foreground text-center">
            No chats yet
          </div>
        ) : (
          sessions.map((s) => {
            const isActive = s.id === activeSessionId;
            return (
              <button
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs
                             transition-colors duration-100 truncate
                             ${isActive
                               ? 'bg-muted text-foreground font-medium'
                               : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
                             }`}
                title={s.title || 'New chat'}
              >
                {s.title || 'New chat'}
              </button>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-border/50">
        <p className="text-[10px] text-muted-foreground/50 text-center">
          Lenny's Podcast · 180 episodes
        </p>
      </div>
    </aside>
  );
}
