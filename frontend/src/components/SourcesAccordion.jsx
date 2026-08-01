/**
 * SourcesAccordion.jsx — Collapsible list of transcript sources with YouTube links.
 * sources: [{ guest, episode_title, youtube_url }]
 */
import { useState } from 'react';
import { ChevronDown, ExternalLink, BookOpen } from 'lucide-react';

export default function SourcesAccordion({ sources = [] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-2.5 border border-border/60 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-bg-base/80
                   hover:bg-bg-elevated transition-colors"
        aria-expanded={open}
        id="sources-toggle"
      >
        <span className="flex items-center gap-2 text-[11px] text-text-muted font-medium">
          <BookOpen className="w-3 h-3 text-accent-primary/70" />
          {sources.length} source{sources.length !== 1 ? 's' : ''} cited
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="animate-fade-in divide-y divide-border/40">
          {sources.map((src, i) => (
            <a
              key={i}
              href={src.youtube_url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2.5 bg-bg-surface
                         hover:bg-bg-elevated transition-colors group"
            >
              <div className="min-w-0 mr-2">
                <p className="text-xs font-semibold text-text-primary truncate group-hover:text-accent-primary transition-colors">
                  {src.guest}
                </p>
                <p className="text-[10px] text-text-muted truncate leading-snug mt-0.5">
                  {src.episode_title}
                </p>
              </div>
              {src.youtube_url && (
                <ExternalLink className="w-3 h-3 text-text-muted group-hover:text-accent-primary flex-shrink-0 transition-colors" />
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
