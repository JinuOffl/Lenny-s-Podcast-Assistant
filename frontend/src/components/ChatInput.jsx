/**
 * ChatInput.jsx — Message input with send button.
 */
import { useState, useRef, useEffect } from 'react';
import { Send, ArrowUpCircle } from 'lucide-react';

const SUGGESTIONS = [
  'What did Brian Chesky say about company culture?',
  'Write a Ship30for30 essay on product-market fit',
  'How do the best growth teams structure their work?',
  'Create an HTML summary of key leadership lessons',
];

export default function ChatInput({ onSend, disabled, placeholder }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div className="flex-shrink-0 bg-bg-base border-t border-border/60 px-4 py-3">
      {/* Suggestion chips (shown when input is empty) */}
      {!value && (
        <div className="flex flex-wrap gap-1.5 mb-2.5">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => { setValue(s); textareaRef.current?.focus(); }}
              className="text-[11px] px-2.5 py-1 rounded-full border border-border/70 text-text-muted
                         bg-bg-elevated/50 hover:border-accent-primary/40 hover:text-text-secondary
                         hover:bg-bg-elevated transition-all duration-150"
            >
              {s.length > 42 ? s.slice(0, 42) + '…' : s}
            </button>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className={`flex items-end gap-2.5 rounded-2xl px-4 py-2.5 transition-all duration-200
        ${disabled
          ? 'bg-bg-elevated/40 border border-border/40 opacity-60'
          : 'bg-bg-elevated border border-border hover:border-accent-primary/30 focus-within:border-accent-primary/60 focus-within:shadow-lg focus-within:shadow-accent-primary/5'
        }`}
      >
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder || 'Ask about growth, product, or request an essay…'}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm text-text-primary
                     placeholder:text-text-muted outline-none leading-relaxed
                     min-h-[22px] max-h-40 disabled:cursor-not-allowed py-0.5"
        />
        <button
          id="chat-send-btn"
          onClick={handleSubmit}
          disabled={!canSend}
          title={canSend ? 'Send message' : 'Type a message first'}
          className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center
                      transition-all duration-150 ${
            canSend
              ? 'bg-accent-primary hover:bg-accent-secondary text-white shadow-md shadow-accent-primary/30 active:scale-90'
              : 'bg-bg-base border border-border text-text-muted cursor-not-allowed'
          }`}
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>

      <p className="text-[10px] text-text-muted text-center mt-1.5">
        <kbd className="px-1.5 py-0.5 bg-bg-elevated border border-border rounded text-[9px] font-mono">Enter</kbd>
        {' '}to send
        &nbsp;·&nbsp;
        <kbd className="px-1.5 py-0.5 bg-bg-elevated border border-border rounded text-[9px] font-mono">Shift+Enter</kbd>
        {' '}for new line
      </p>
    </div>
  );
}
