/**
 * ProviderToggle.jsx — Pill toggle for Local / Cloud.
 * Active option always shows white bg + a small green dot.
 */
import { Cpu, Cloud } from 'lucide-react';

export default function ProviderToggle({ provider, onChange, modelName }) {
  const options = [
    { value: 'ollama',    label: 'Local',  Icon: Cpu   },
    { value: 'anthropic', label: 'Cloud',  Icon: Cloud },
  ];

  return (
    <div className="flex items-center gap-2">
      {modelName && (
        <span className="text-[10px] text-text-muted font-mono hidden sm:flex items-center gap-1">
          <span className="text-text-muted/60">model:</span>
          {modelName}
        </span>
      )}
      <div className="flex items-center bg-bg-elevated border border-border rounded-lg p-0.5">
        {options.map(({ value, label, Icon }) => {
          const isActive = provider === value;
          return (
            <button
              key={value}
              id={`provider-toggle-${value}`}
              onClick={() => onChange(value)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium
                          transition-all duration-150 ${
                isActive
                  ? 'bg-white text-black shadow-sm'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <Icon className="w-3 h-3" />
              {label}
              {/* Always-visible active dot */}
              {isActive && (
                <span className="w-1.5 h-1.5 rounded-full bg-skill-artifact flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

