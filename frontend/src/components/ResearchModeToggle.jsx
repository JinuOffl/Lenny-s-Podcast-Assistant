/**
 * ResearchModeToggle.jsx — "Research" mode pill button near the chat input.
 * Mimics GPT's "Search" / Gemini's "Deep Research" plugin button.
 *
 * Off: subtle border pill, muted text
 * On:  glowing amber, animated pulse dot, "Research Active"
 *
 * Props:
 *   researchMode: bool
 *   onChange: (bool) => void
 *   disabled: bool
 */
import { Microscope } from 'lucide-react';

export default function ResearchModeToggle({ researchMode, onChange, disabled }) {
  return (
    <button
      id="research-mode-toggle"
      onClick={() => {
        if (!disabled) onChange(!researchMode);
      }}
      disabled={disabled}
      title={researchMode ? 'Research Mode active — 5-agent pipeline' : 'Enable Research Mode'}
      className="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl
                 text-[11px] font-semibold tracking-wide border transition-all duration-200
                 disabled:cursor-not-allowed disabled:opacity-40"
      style={researchMode ? {
        borderColor: 'rgba(249,115,22,0.5)',
        color: 'rgb(249,115,22)',
        background: 'rgba(249,115,22,0.08)',
        boxShadow: '0 0 12px rgba(249,115,22,0.2)',
      } : {
        borderColor: 'rgba(255,255,255,0.1)',
        color: 'rgba(255,255,255,0.4)',
        background: 'transparent',
      }}
    >
      {/* Animated pulse dot when active */}
      {researchMode ? (
        <span className="relative flex h-1.5 w-1.5 flex-shrink-0">
          <span
            className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            style={{ background: 'rgb(249,115,22)' }}
          />
          <span
            className="relative inline-flex rounded-full h-1.5 w-1.5"
            style={{ background: 'rgb(249,115,22)' }}
          />
        </span>
      ) : (
        <Microscope className="w-3 h-3 flex-shrink-0" />
      )}
      {researchMode ? 'Research Active' : 'Research'}
    </button>
  );
}
