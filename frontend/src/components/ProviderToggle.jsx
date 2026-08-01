/**
 * ProviderToggle.jsx — Minimal pill toggle for Local / Cloud.
 * White border when active, no orange.
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
        <span className="text-[10px] text-text-muted font-mono hidden sm:block">{modelName}</span>
      )}
      <div className="flex items-center bg-bg-elevated border border-border rounded-lg p-0.5">
        {options.map(({ value, label, Icon }) => (
          <button
            key={value}
            id={`provider-toggle-${value}`}
            onClick={() => onChange(value)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium
                        transition-all duration-150 ${
              provider === value
                ? 'bg-white text-black shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <Icon className="w-3 h-3" />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
