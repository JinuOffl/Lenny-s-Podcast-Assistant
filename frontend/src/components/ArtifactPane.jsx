/**
 * ArtifactPane.jsx — Split-pane artifact viewer.
 * Shows rendered preview (sandboxed iframe for HTML, markdown for .md)
 * and a raw source tab with copy button.
 *
 * props:
 *   artifact: { type: 'html'|'markdown', content: string }
 *   onClose: () => void
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, X, Code2, Eye, Layers } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';

export default function ArtifactPane({ artifact, onClose }) {
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState('preview');

  if (!artifact) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may fail in some contexts
    }
  };

  const isHtml = artifact.type === 'html';

  return (
    <div className="flex flex-col h-full bg-bg-surface animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-skill-artifact/10 border border-skill-artifact/30
                          flex items-center justify-center flex-shrink-0">
            <Layers className="w-3.5 h-3.5 text-skill-artifact" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary leading-tight">Artifact</p>
            <p className="text-[9px] text-text-muted font-mono leading-tight">
              {isHtml ? 'text/html' : 'text/markdown'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            title="Copy source"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
                       text-text-secondary border border-border/60 hover:border-accent-primary/40
                       hover:text-accent-primary transition-all duration-150"
            id="artifact-copy-btn"
          >
            {copied
              ? <Check className="w-3.5 h-3.5 text-skill-artifact" />
              : <Copy className="w-3.5 h-3.5" />
            }
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
            id="artifact-close-btn"
            title="Close artifact pane"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs.Root value={tab} onValueChange={setTab} className="flex flex-col flex-1 min-h-0">
        <Tabs.List className="flex border-b border-border px-3 flex-shrink-0 gap-0.5">
          {[
            { value: 'preview', icon: Eye,   label: 'Preview' },
            { value: 'source',  icon: Code2, label: 'Source'  },
          ].map(({ value, icon: Icon, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold border-b-2 transition-all duration-150
                ${tab === value
                  ? 'border-accent-primary text-accent-primary'
                  : 'border-transparent text-text-muted hover:text-text-secondary'}`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* Preview tab */}
        <Tabs.Content value="preview" className="flex-1 min-h-0 overflow-hidden">
          {isHtml ? (
            <iframe
              id="artifact-iframe"
              title="Artifact preview"
              srcDoc={artifact.content}
              className="w-full h-full border-0 bg-white"
              sandbox="allow-scripts allow-forms allow-popups allow-modals"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="h-full overflow-y-auto p-5">
              <div className="prose-lenny max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {artifact.content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </Tabs.Content>

        {/* Source tab */}
        <Tabs.Content value="source" className="flex-1 min-h-0 overflow-hidden">
          <div className="h-full overflow-auto bg-bg-base/60">
            <pre className="p-5 text-xs font-mono text-text-secondary whitespace-pre-wrap break-words leading-relaxed">
              {artifact.content}
            </pre>
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
