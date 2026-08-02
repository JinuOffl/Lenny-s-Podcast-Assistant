/**
 * ChatInput.jsx — Auto-resize composer, ChatGPT-style.
 * Centered max-width 760px, Research Mode toggle left of send button.
 * Capability chips appear below input on empty chat state.
 */
import { useState, useRef, useEffect } from 'react';
import { ArrowUp, BookOpen, BarChart2, Lightbulb, Layers } from 'lucide-react';
import ResearchModeToggle from './ResearchModeToggle';

const CHIPS = [
  {
    icon: BookOpen,
    label: 'Essay',
    prompt: 'Write a Ship30for30 essay on product-market fit',
    color: 'rgba(112,89,196,0.6)',
  },
  {
    icon: Lightbulb,
    label: 'Q&A',
    prompt: 'What did Brian Chesky say about company culture?',
    color: 'rgba(78,122,199,0.6)',
  },
  {
    icon: BarChart2,
    label: 'Insights',
    prompt: 'What are the top retention strategies from Lenny\'s podcast?',
    color: 'rgba(61,144,104,0.6)',
  },
  {
    icon: Layers,
    label: 'Dashboard',
    prompt: 'Create an HTML chart showing growth frameworks from the podcast',
    color: 'rgba(196,133,26,0.6)',
  },
];

export default function ChatInput({ onSend, disabled, placeholder, researchMode, onResearchModeChange, hasMessages }) {

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
  const showChips = !hasMessages && value.trim() === '' && !disabled;

  return (
    <div className="flex-shrink-0 px-4 py-4 bg-bg-base">
      <div className="max-w-[760px] mx-auto">
        {/* Capability chips — only on empty state */}
        {showChips && (
          <div className="flex gap-2 mb-3 flex-wrap justify-center">
            {CHIPS.map((chip) => {
              const Icon = chip.icon;
              return (
                <button
                  key={chip.label}
                  onClick={() => onSend(chip.prompt)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border
                             bg-bg-surface text-text-secondary text-xs font-medium
                             hover:border-white/20 hover:text-text-primary hover:bg-bg-elevated
                             transition-all duration-150 group"
                >
                  <Icon
                    className="w-3 h-3 flex-shrink-0"
                    style={{ color: chip.color }}
                  />
                  {chip.label}
                </button>
              );
            })}
          </div>
        )}

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
