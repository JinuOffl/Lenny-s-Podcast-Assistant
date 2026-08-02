/**
 * ChatInput.jsx — Auto-resize composer, ChatGPT-style.
 * Centered max-width 760px, Research Mode toggle left of send button.
 */
import { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';
import ResearchModeToggle from './ResearchModeToggle';

export default function ChatInput({ onSend, disabled, placeholder, researchMode, onResearchModeChange }) {

  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize
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
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div className="flex-shrink-0 px-4 py-4 bg-bg-base">
      <div className="max-w-[760px] mx-auto">
        {/* Composer */}
        <div className={`flex items-end gap-3 rounded-2xl px-4 py-3 border transition-all duration-200 ${
          disabled
            ? 'bg-bg-surface border-border/40 opacity-60'
            : 'bg-bg-surface border-border hover:border-border/80 focus-within:border-white/20'
        }`}>
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder || 'Ask anything about growth…'}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-text-primary
                       placeholder:text-text-muted outline-none leading-relaxed
                       min-h-[22px] max-h-40 disabled:cursor-not-allowed py-0.5"
          />
          {/* Research Mode toggle */}
          <ResearchModeToggle
            researchMode={researchMode}
            onChange={onResearchModeChange}
            disabled={disabled}
          />
          <button
            id="chat-send-btn"
            onClick={handleSubmit}
            disabled={!canSend}
            title="Send message"
            className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center
                        transition-all duration-150 ${
              canSend
                ? 'bg-white text-black hover:bg-white/90 active:scale-90 shadow-sm'
                : 'bg-bg-elevated border border-border text-text-muted cursor-not-allowed'
            }`}
          >
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Footer hint */}
        <p className="text-[10px] text-text-muted text-center mt-2">
          <kbd className="px-1 bg-bg-elevated border border-border rounded text-[9px] font-mono">Enter</kbd>
          {' '}to send · <kbd className="px-1 bg-bg-elevated border border-border rounded text-[9px] font-mono">Shift+Enter</kbd>
          {' '}new line
        </p>
      </div>
    </div>
  );
}
