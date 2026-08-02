/**
 * ResearchStats.jsx — Compact collapsible stats row shown below Research Mode responses.
 * Shows: chunks found · episodes searched · search hops · word count
 *
 * Props:
 *   stats: { chunks_found: number, episodes: number, search_hops: number, word_count: number }
 *   healingAttempts: number
 */
import { useState } from 'react';
import { ChevronDown, Database, BookOpen, GitBranch, FileText, Wrench } from 'lucide-react';

export default function ResearchStats({ stats, healingAttempts = 0 }) {
  const [expanded, setExpanded] = useState(false);
  if (!stats) return null;

  const items = [
    { icon: Database,   label: `${stats.chunks_found ?? 0} chunks` },
    { icon: BookOpen,   label: `${stats.episodes ?? 0} episode${stats.episodes !== 1 ? 's' : ''}` },
    { icon: GitBranch,  label: `${stats.search_hops ?? 1} search hop${stats.search_hops !== 1 ? 's' : ''}` },
    ...(stats.word_count > 0 ? [{ icon: FileText, label: `${stats.word_count} words` }] : []),
  ];

  return (
    <div className="mt-2">
      {/* Self-heal banner */}
      {healingAttempts > 0 && (
        <div
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg mb-1.5 text-[10px] font-medium"
          style={{
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.2)',
            color: 'rgb(251,191,36)',
          }}
        >
          <Wrench className="w-3 h-3 flex-shrink-0" />
          Self-healed {healingAttempts}× — ValidatorAgent fixed errors automatically
        </div>
      )}

      {/* Stats toggle */}
      <button
        id="research-stats-toggle"
        onClick={() => setExpanded(e => !e)}
        className="flex items-center gap-1.5 text-[10px] transition-colors duration-150"
        style={{ color: 'rgba(255,255,255,0.25)' }}
        onMouseEnter={e => e.currentTarget.style.color = 'rgba(255,255,255,0.45)'}
        onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.25)'}
      >
        <ChevronDown
          className="w-3 h-3 transition-transform duration-150"
          style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
        Research details
      </button>

      {/* Expanded stats */}
      {expanded && (
        <div
          className="flex flex-wrap gap-2 mt-1.5 px-2.5 py-2 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          {items.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-1 text-[10px]"
              style={{ color: 'rgba(255,255,255,0.4)' }}
            >
              <Icon className="w-3 h-3" style={{ color: 'rgba(249,115,22,0.6)' }} />
              {label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
