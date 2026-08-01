/**
 * ProviderToggle.jsx — Segmented control to switch LLM provider.
 */
import { Cpu, Cloud } from 'lucide-react';

export default function ProviderToggle({ provider, onChange, modelName }) {
  const options = [
    { value: 'ollama',    label: 'Local',  Icon: Cpu   },
    { value: 'anthropic', label: 'Cloud',  Icon: Cloud },
  ];

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center bg-bg-elevated border border-border/80 rounded-xl p-0.5 gap-0.5">
        {options.map(({ value, label, Icon }) => (
          <button
            key={value}
            id={`provider-toggle-${value}`}
            onClick={() => onChange(value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                        transition-all duration-200 ${
              provider === value
                ? 'bg-accent-primary text-white shadow-sm shadow-accent-primary/30'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <Icon className="w-3 h-3" />
            {label}
          </button>
        ))}
      </div>
      {modelName && (
        <span className="text-[9px] text-text-muted font-mono opacity-70">{modelName}</span>
      )}
    </div>
  );
}
