/**
 * ThinkingDots.jsx — Gray pulsing dots with "Thinking" label.
 * Keeps the same animation timing the user likes, recolored to monochromatic gray.
 */
export default function ThinkingDots() {
  return (
    <div className="flex items-start gap-3 px-4 py-3 max-w-[760px] mx-auto w-full animate-fade-in">
      {/* ● dot matching AI messages */}
      <div className="w-2 h-2 rounded-full bg-white/30 flex-shrink-0 mt-1.5" />

      {/* Thinking label + dots */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted font-medium">Thinking</span>
        <div className="flex items-center gap-1">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
        </div>
      </div>
    </div>
  );
}
