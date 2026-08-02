/**
 * SkillBadge.jsx — Border-only pill, no filled color backgrounds.
 * Monochromatic style matching Nothing design philosophy.
 * Handles research:* prefixed skills from Research Mode.
 *
 * Part 2 Item 1: colors desaturated/darkened, labels in monospace uppercase wider tracking.
 */

const SKILL_CONFIG = {
  qa: {
    label: 'Q&A',
    // was #5B8DEF — slightly desaturated, pulled darker
    color: '#4E7AC7',
  },
  ship30for30: {
    label: 'ESSAY',
    // was #8B6EE8 — desaturated toward slate-purple
    color: '#7059C4',
  },
  artifact: {
    label: 'ARTIFACT',
    // was #4CAF82 — pulled darker and less saturated
    color: '#3D9068',
  },
  multi: {
    label: 'MULTI',
    // was #F5A623 (amber) — darkened/desaturated
    color: '#C4851A',
  },
  followup: {
    label: 'FOLLOW-UP',
    // was #9E9E9E — kept, neutral gray reads fine
    color: '#7A7A7A',
  },
  // Research Mode variants — was #F97316, pull toward muted amber
  'research:qa': {
    label: 'RESEARCH',
    color: '#C06A10',
  },
  'research:ship30for30': {
    label: 'RESEARCH ESSAY',
    color: '#C06A10',
  },
  'research:multi': {
    label: 'RESEARCH · ARTIFACT',
    color: '#C06A10',
  },
  'research:followup': {
    label: 'RESEARCH FOLLOW-UP',
    color: '#C06A10',
  },
};

export default function SkillBadge({ skill }) {
  const cfg = SKILL_CONFIG[skill] || SKILL_CONFIG[skill?.replace('research:', '')] || SKILL_CONFIG.qa;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border"
      style={{
        borderColor: `${cfg.color}50`,
        color: `${cfg.color}DD`,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9px',
        fontWeight: 500,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
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
