/**
 * SkillBadge.jsx — Border-only pill, no filled color backgrounds.
 * Monochromatic style matching Nothing design philosophy.
 * Handles research:* prefixed skills from Research Mode.
 */

const SKILL_CONFIG = {
  qa: {
    label: 'Q&A',
    color: '#5B8DEF',
  },
  ship30for30: {
    label: 'Essay',
    color: '#8B6EE8',
  },
  artifact: {
    label: 'Artifact',
    color: '#4CAF82',
  },
  multi: {
    label: '⚡ Multi',
    color: '#F5A623',
  },
  followup: {
    label: 'Follow-up',
    color: '#9E9E9E',
  },
  // Research Mode variants
  'research:qa': {
    label: '🔬 Research',
    color: '#F97316',
  },
  'research:ship30for30': {
    label: '🔬 Research Essay',
    color: '#F97316',
  },
  'research:multi': {
    label: '🔬 Research + Artifact',
    color: '#F97316',
  },
  'research:followup': {
    label: '🔬 Research Follow-up',
    color: '#F97316',
  },
};

export default function SkillBadge({ skill }) {
  const cfg = SKILL_CONFIG[skill] || SKILL_CONFIG[skill?.replace('research:', '')] || SKILL_CONFIG.qa;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide border"
      style={{
        borderColor: `${cfg.color}40`,
        color: `${cfg.color}CC`,
      }}
    >
      <span
        className="w-1 h-1 rounded-full flex-shrink-0"
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}
