/**
 * SkillBadge.jsx — Colored pill showing which skill was used.
 */

const SKILL_CONFIG = {
  qa: {
    label: 'Q&A',
    bg:    'bg-skill-qa/10',
    border:'border-skill-qa/30',
    text:  'text-skill-qa',
    dot:   'bg-skill-qa',
  },
  ship30for30: {
    label: 'Essay',
    bg:    'bg-skill-ship30/10',
    border:'border-skill-ship30/30',
    text:  'text-skill-ship30',
    dot:   'bg-skill-ship30',
  },
  artifact: {
    label: 'Artifact',
    bg:    'bg-skill-artifact/10',
    border:'border-skill-artifact/30',
    text:  'text-skill-artifact',
    dot:   'bg-skill-artifact',
  },
};

export default function SkillBadge({ skill }) {
  const cfg = SKILL_CONFIG[skill] || SKILL_CONFIG.qa;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold
                      border ${cfg.bg} ${cfg.border} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
