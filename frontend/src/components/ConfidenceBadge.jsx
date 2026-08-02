/**
 * ConfidenceBadge.jsx — Color-coded confidence indicator for Research Mode responses.
 * Shows how many sources back the response.
 *
 * high   → green  (5+ sources)
 * medium → amber  (2-4 sources)
 * low    → red    (0-1 sources)
 *
 * Props:
 *   confidence: "high" | "medium" | "low"
 */

const CONFIG = {
  high:   { color: 'rgb(74,222,128)',  bg: 'rgba(74,222,128,0.08)',  border: 'rgba(74,222,128,0.25)', label: 'High confidence' },
  medium: { color: 'rgb(251,191,36)',  bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.25)', label: 'Medium confidence' },
  low:    { color: 'rgb(248,113,113)', bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.25)', label: 'Low confidence' },
};

export default function ConfidenceBadge({ confidence }) {
  const cfg = CONFIG[confidence] || CONFIG.medium;
  return (
    <span
      id={`confidence-badge-${confidence}`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border"
      style={{ color: cfg.color, background: cfg.bg, borderColor: cfg.border }}
      title={`Research confidence: ${confidence}`}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}
