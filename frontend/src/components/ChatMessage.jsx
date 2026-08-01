/**
 * ChatMessage.jsx — Single message row.
 *
 * User:     right-aligned gray pill
 * Assistant: left-aligned, no bubble, ● dot prefix, hover copy action
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Layers } from 'lucide-react';
import SkillBadge from './SkillBadge';
import SourcesAccordion from './SourcesAccordion';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };
  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-md text-text-muted hover:text-text-secondary
                 hover:bg-bg-elevated transition-all duration-150"
      title="Copy message"
    >
      {copied
        ? <Check className="w-3.5 h-3.5 text-skill-artifact" />
        : <Copy className="w-3.5 h-3.5" />
      }
    </button>
  );
}

export default function ChatMessage({ role, content, skillUsed, sources, artifact, onOpenArtifact, isStreaming }) {
  const [hovered, setHovered] = useState(false);
  const isUser = role === 'user';

  /* ── User message ── */
  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2 animate-fade-up">
        <div className="max-w-[72%] bg-bg-user-msg border border-border text-text-primary
                        text-sm leading-relaxed px-4 py-2.5 rounded-2xl rounded-br-sm">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    );
  }

  /* ── Assistant message ── */
  return (
    <div
      className="group flex flex-col px-4 py-3 animate-fade-up max-w-[760px] mx-auto w-full"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Message content row */}
      <div className="flex items-start gap-3">
        {/* ● dot */}
        <div className="w-2 h-2 rounded-full bg-white/80 flex-shrink-0 mt-2" />

        {/* Text */}
        <div className="flex-1 min-w-0 prose-chat">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-text-muted ml-0.5 animate-pulse" aria-hidden />
          )}
        </div>
      </div>

      {/* Action bar (hover-revealed) */}
      <div className={`flex items-center gap-1 mt-2 pl-5 transition-all duration-150 ${hovered ? 'opacity-100' : 'opacity-0'}`}>
        <CopyButton text={content} />
        {skillUsed && <SkillBadge skill={skillUsed} />}
        {artifact && (
          <button
            onClick={() => onOpenArtifact?.(artifact)}
            id="open-artifact-btn"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium
                       border border-skill-artifact/30 text-skill-artifact/80
                       hover:border-skill-artifact/60 hover:text-skill-artifact
                       transition-all duration-150 ml-1"
          >
            <Layers className="w-3 h-3" />
            View artifact
          </button>
        )}
      </div>

      {/* Sources */}
      {sources?.length > 0 && (
        <div className="pl-5 mt-1">
          <SourcesAccordion sources={sources} />
        </div>
      )}
    </div>
  );
}
