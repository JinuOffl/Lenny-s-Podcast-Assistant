/**
 * ChatMessage.jsx — Single message row.
 *
 * User:      right-aligned gray pill
 * Assistant: left-aligned, dot prefix, hover-copy, streaming cursor,
 *            thinking dots (before first token), artifact preview card,
 *            AgentTracker (Research Mode), ConfidenceBadge, ResearchStats
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Layers, Code2, FileText, ExternalLink, RotateCcw } from 'lucide-react';
import SkillBadge from './SkillBadge';
import SourcesAccordion from './SourcesAccordion';
import AgentTracker from './AgentTracker';
import ConfidenceBadge from './ConfidenceBadge';
import ResearchStats from './ResearchStats';

// Item 7: copy message text
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }); }}
      className="flex items-center gap-1 p-1.5 rounded-md text-text-muted hover:text-text-secondary hover:bg-bg-elevated transition-all duration-150"
      title="Copy message"
    >
      {copied
        ? <><Check className="w-3.5 h-3.5 text-skill-artifact" /><span className="text-[10px] text-skill-artifact">Copied!</span></>
        : <><Copy className="w-3.5 h-3.5" /></>}
    </button>
  );
}

// Item 6: retry/regenerate
function RetryButton({ onRetry }) {
  return (
    <button
      onClick={onRetry}
      className="flex items-center gap-1 p-1.5 rounded-md text-text-muted hover:text-text-secondary hover:bg-bg-elevated transition-all duration-150"
      title="Regenerate response"
    >
      <RotateCcw className="w-3.5 h-3.5" />
    </button>
  );
}

/** Mini artifact card that appears inline in the chat panel */
function ArtifactCard({ artifact, onClick }) {
  const isHtml = artifact?.type === 'html';
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 w-full max-w-[340px] mt-3 px-3.5 py-2.5
                 rounded-xl border border-skill-artifact/25 bg-bg-elevated
                 hover:border-skill-artifact/50 hover:bg-bg-elevated/80
                 transition-all duration-150 text-left group"
    >
      <div className="w-8 h-8 rounded-lg bg-skill-artifact/10 border border-skill-artifact/20
                      flex items-center justify-center flex-shrink-0">
        {isHtml
          ? <Code2 className="w-4 h-4 text-skill-artifact" />
          : <FileText className="w-4 h-4 text-skill-artifact" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-text-primary truncate">
          {isHtml ? 'Interactive HTML' : 'Markdown Document'}
        </p>
        <p className="text-[10px] text-skill-artifact mt-0.5">Click to open preview →</p>
      </div>
    </button>
  );
}

/** Wraps a partial HTML snippet into a full dark document with Chart.js */
function wrapHtml(code) {
  const trimmed = code.trim().toLowerCase();
  if (trimmed.startsWith('<!doctype') || trimmed.startsWith('<html')) {
    return code; // already a full document
  }
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"><\/script>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"><\/script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0d0d0d; color: #f2f2f2; padding: 20px;
           font-family: 'Inter', system-ui, sans-serif; min-height: 100vh; }
    canvas { max-width: 100%; }
  </style>
</head>
<body>
${code}
</body>
</html>`;
}

/** HTML code block — renders with an "Open Preview" button */
function HtmlCodeBlock({ code, onOpenArtifact }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative my-3 rounded-xl overflow-hidden border border-skill-artifact/20">
      <div className="flex items-center justify-between px-3 py-1.5 bg-bg-elevated border-b border-skill-artifact/15">
        <span className="text-[10px] font-mono text-skill-artifact/70 font-semibold tracking-wide">html</span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1800); }}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-text-muted hover:text-text-secondary transition-colors"
          >
            {copied ? <Check className="w-3 h-3 text-skill-artifact" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={() => onOpenArtifact?.({ type: 'html', content: wrapHtml(code) })}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium
                       bg-skill-artifact/10 text-skill-artifact border border-skill-artifact/25
                       hover:bg-skill-artifact/20 transition-all"
          >
            <ExternalLink className="w-3 h-3" /> Open Preview
          </button>
        </div>
      </div>
      <pre className="p-3 text-xs font-mono text-text-secondary bg-bg-base/60 overflow-x-auto max-h-48 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}


/**
 * AgentStatus — single animated row that transitions in-place.
 * Shows "Thinking..." by default; swaps to agentStep label when one arrives.
 * Mimics Claude's "Figuring... → Searching... → Writing..." UX.
 * Dots always animate regardless of step — consistent across all states.
 */
function AgentStatus({ step }) {
  const label = step || 'Thinking';
  return (
    <div key={label} className="flex items-center gap-1.5 h-5 animate-fade-up">
      <span className="text-sm text-text-muted italic">{label}</span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1 h-1 rounded-full bg-text-muted animate-thinking"
          style={{ animationDelay: `${i * 0.22}s` }}
        />
      ))}
    </div>
  );
}

export default function ChatMessage({
  role, content, skillUsed, sources, artifact, onOpenArtifact,
  isStreaming, agentStep,
  // Research Mode extras
  agentSteps = [], confidence, researchStats, healingAttempts = 0,
  // Pass 2 features
  msgId, onRetry,
}) {
  const [hovered, setHovered] = useState(false);
  const isUser = role === 'user';

  /* ── User message ── */
  if (isUser) {
    return (
      <div className="flex justify-end items-end gap-2 px-4 py-2 animate-fade-up">
        <div className="max-w-[72%] bg-bg-user-msg border border-white/10 text-text-primary
                        text-sm leading-relaxed px-4 py-2.5 rounded-2xl rounded-br-md shadow-sm">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
        {/* User avatar */}
        <div className="w-6 h-6 rounded-full bg-white/15 border border-white/20 flex items-center justify-center flex-shrink-0 mb-0.5">
          <span className="text-[10px] font-semibold text-text-primary leading-none">U</span>
        </div>
      </div>
    );
  }

  const isEmpty = !content || content.trim() === '';

  /** Custom code block renderer — HTML blocks get Open Preview button */
  const CodeBlock = ({ node, inline, className, children, ...props }) => {
    const lang = /language-(\w+)/.exec(className || '')?.[1];
    const code = String(children).replace(/\n$/, '');
    if (!inline && lang === 'html') {
      return <HtmlCodeBlock code={code} onOpenArtifact={onOpenArtifact} />;
    }
    return (
      <code
        className={`${inline ? 'bg-bg-elevated px-1 py-0.5 rounded text-xs font-mono text-text-secondary' : 'block bg-bg-base/60 p-3 rounded-lg text-xs font-mono text-text-secondary overflow-x-auto'} ${className || ''}`}
        {...props}
      >
        {children}
      </code>
    );
  };

  /* ── Assistant message ── */
  return (
    <div
      className="group flex flex-col px-4 py-3 animate-fade-up max-w-[760px] mx-auto w-full"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Message content row */}
      <div className="flex items-start gap-3">
        {/* L avatar */}
        <div className="w-6 h-6 rounded-md bg-white flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-black font-black text-[10px] leading-none">L</span>
        </div>

        {/* Text area */}
        <div className="flex-1 min-w-0 prose-chat">
          {isEmpty && isStreaming
            ? (
              /* Pre-content: label swaps in-place — key remounts on each step change */
              <AgentStatus key={agentStep || 'thinking'} step={agentStep} />
            )
            : (
              <>
                {/* AgentTracker — shown above content in Research Mode */}
                {isStreaming && agentSteps.length > 0 && (
                  <AgentTracker steps={agentSteps} isActive={isStreaming} />
                )}
                {/* Once tokens arrive, compact step above content while streaming */}
                {agentStep && isStreaming && (
                  <AgentStatus key={agentStep} step={agentStep} />
                )}
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>{content}</ReactMarkdown>
                {isStreaming && (
                  <span className="inline-block w-0.5 h-4 bg-text-muted ml-0.5 animate-pulse" aria-hidden />
                )}
              </>
            )
          }
        </div>
      </div>

      {/* Artifact preview card — shown inline in chat */}
      {artifact && !isStreaming && (
        <div className="pl-9">
          <ArtifactCard artifact={artifact} onClick={() => onOpenArtifact?.(artifact)} />
        </div>
      )}

      {/* Item 9: Skill badge — always-visible under message */}
      {skillUsed && !isStreaming && !isEmpty && (
        <div className="flex items-center gap-1.5 pl-9 mt-1.5">
          <SkillBadge skill={skillUsed} />
          {confidence && skillUsed?.startsWith('research:') && (
            <ConfidenceBadge confidence={confidence} />
          )}
        </div>
      )}

      {/* Action bar (hover-revealed): copy + retry + artifact link */}
      {!isStreaming && !isEmpty && (
        <div className={`flex items-center flex-wrap gap-0.5 mt-1 pl-9 transition-all duration-150 ${hovered ? 'opacity-100' : 'opacity-0'}`}>
          {/* Item 7: copy */}
          <CopyButton text={content} />
          {/* Item 6: retry */}
          {onRetry && <RetryButton onRetry={() => onRetry(msgId)} />}
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
      )}

      {/* Sources */}
      {sources?.length > 0 && !isStreaming && (
        <div className="pl-9 mt-1">
          <SourcesAccordion sources={sources} />
        </div>
      )}

      {/* Research Stats + self-heal banner (Research Mode only) */}
      {researchStats && !isStreaming && (
        <div className="pl-9 mt-0.5">
          <ResearchStats stats={researchStats} healingAttempts={healingAttempts} />
        </div>
      )}
    </div>
  );
}
