/**
 * ThinkingDots.jsx — Animated "AI is thinking" indicator.
 */
export default function ThinkingDots() {
  return (
    <div className="flex items-center gap-3 px-5 py-3 animate-fade-in">
      {/* Assistant avatar */}
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent-primary to-amber-500
                      flex items-center justify-center flex-shrink-0 shadow-sm shadow-accent-primary/20">
        <span className="text-[11px] font-bold text-white">L</span>
      </div>

      <div className="flex items-center gap-1.5 bg-bg-surface border border-border/60
                      rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <span className="text-[11px] text-text-muted font-medium mr-2 tracking-wide">Thinking</span>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="thinking-dot w-1.5 h-1.5 bg-accent-primary block"
            style={{ animationDelay: `${i * 0.16}s` }}
          />
        ))}
      </div>
    </div>
  );
}
