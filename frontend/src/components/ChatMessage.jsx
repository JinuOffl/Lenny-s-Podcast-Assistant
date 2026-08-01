/**
 * ChatMessage.jsx — Single message bubble.
 *
 * props:
 *   role:          'user' | 'assistant'
 *   content:       string
 *   skillUsed:     'qa' | 'ship30for30' | 'artifact' | null
 *   sources:       [{ guest, episode_title, youtube_url }]
 *   artifact:      { type, content } | null
 *   onOpenArtifact: (artifact) => void
 *   index:         number  (for stagger animation)
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Layers } from 'lucide-react';
import SkillBadge from './SkillBadge';
import SourcesAccordion from './SourcesAccordion';

const UserAvatar = () => (
  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600
                  flex items-center justify-center flex-shrink-0 shadow-sm">
    <span className="text-[11px] font-bold text-white">U</span>
  </div>
);

const AssistantAvatar = () => (
  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent-primary to-amber-500
                  flex items-center justify-center flex-shrink-0 shadow-sm shadow-accent-primary/25">
    <span className="text-[11px] font-bold text-white">L</span>
  </div>
);

export default function ChatMessage({ role, content, skillUsed, sources, artifact, onOpenArtifact, index = 0 }) {
  const isUser = role === 'user';

  return (
    <div
      className={`flex gap-3 px-5 py-3 animate-fade-up ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      style={{ animationDelay: `${Math.min(index * 30, 150)}ms` }}
    >
      {isUser ? <UserAvatar /> : <AssistantAvatar />}

      <div className={`max-w-[82%] min-w-0 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-accent-primary/10 border border-accent-primary/20 text-text-primary rounded-tr-sm'
              : 'bg-bg-surface border border-border/60 text-text-primary rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose-lenny min-w-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer: skill badge + artifact button */}
        {!isUser && (
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {skillUsed && <SkillBadge skill={skillUsed} />}
            {artifact && (
              <button
                onClick={() => onOpenArtifact?.(artifact)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium
                           bg-skill-artifact/10 border border-skill-artifact/30 text-skill-artifact
                           hover:bg-skill-artifact/20 hover:border-skill-artifact/50
                           transition-all duration-150 active:scale-95"
                id="open-artifact-btn"
              >
                <Layers className="w-3 h-3" />
                View artifact
              </button>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && sources?.length > 0 && (
          <div className="w-full mt-1.5">
            <SourcesAccordion sources={sources} />
          </div>
        )}
      </div>
    </div>
  );
}
