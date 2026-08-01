/**
 * SourcesAccordion.jsx — Clean minimal source list.
 * Sits below AI message, left-border style matching Nothing cards.
 */
import { useState } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';

export default function SourcesAccordion({ sources = [] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-text-muted
                   hover:text-text-secondary transition-colors duration-150 group"
        aria-expanded={open}
        id="sources-toggle"
      >
        <span className="font-medium">
          {sources.length} source{sources.length !== 1 ? 's' : ''}
        </span>
        <ChevronDown
          className={`w-3 h-3 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="mt-2 border-l-2 border-border pl-3 space-y-0 animate-fade-in">
          {sources.map((src, i) => (
            <a
              key={i}
              href={src.youtube_url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between py-1.5 group"
            >
              <div className="min-w-0 mr-3">
                <p className="text-xs font-medium text-text-secondary group-hover:text-text-primary transition-colors truncate">
                  {src.guest}
                </p>
                <p className="text-[10px] text-text-muted truncate mt-0.5 leading-snug">
                  {src.episode_title}
                </p>
              </div>
              {src.youtube_url && (
                <ExternalLink className="w-3 h-3 text-text-muted group-hover:text-text-secondary flex-shrink-0 transition-colors" />
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
