/**
 * AgentTracker.jsx — Live pipeline visualization shown above streaming responses
 * in Research Mode.
 *
 * Displays the 5-agent pipeline as a horizontal sequence:
 *   OrchestratorAgent → ResearchAgent → WriterAgent → ArtifactAgent → ValidatorAgent
 *
 * Each agent can be: pending | active | done | healing
 *
 * Design: monochrome dark palette — no orange/green/yellow.
 * Active = white, Done = white/40, Healing = white/60 pulse, Pending = white/15
 *
 * Props:
 *   steps: Array<{agent: string, step: string}>  — accumulated from SSE events
 *   isActive: bool — whether Research Mode is streaming
 */
import { Check, Loader2, Wrench, Circle } from 'lucide-react';

const PIPELINE = [
  { key: 'OrchestratorAgent', label: 'Orchestrator', short: 'Plan'   },
  { key: 'ResearchAgent',     label: 'Research',     short: 'Search' },
  { key: 'WriterAgent',       label: 'Writer',       short: 'Write'  },
  { key: 'ArtifactAgent',     label: 'Artifact',     short: 'Build'  },
  { key: 'ValidatorAgent',    label: 'Validator',    short: 'QC'     },
];

/** Strip emojis and leading emoji + space from step strings */
function cleanStep(step) {
  return step
    .replace(/[\u{1F000}-\u{1FFFF}]/gu, '')   // emoji block
    .replace(/^[\s⚠️✅🔧🔍📋✍️🎨⏳💬🏁🧠]+/, '')  // leading symbols
    .trim();
}

function getAgentStatus(agentKey, steps) {
  const agentSteps = steps.filter(s => s.agent === agentKey);
  if (agentSteps.length === 0) return 'pending';
  const lastStep = (agentSteps[agentSteps.length - 1].step || '').toLowerCase();
  // Healing / self-repair
  if (lastStep.includes('fix') || lastStep.includes('repair') || lastStep.includes('heal')) return 'healing';
  // Done — terminal phrases
  if (
    lastStep.includes('done') || lastStep.includes('complete') ||
    lastStep.includes('found') || lastStep.includes('planning') ||
    lastStep.includes('valid') || lastStep.startsWith('found ')
  ) return 'done';
  return 'active';
}

function getLatestStep(agentKey, steps) {
  const agentSteps = steps.filter(s => s.agent === agentKey);
  return agentSteps[agentSteps.length - 1]?.step || '';
}

export default function AgentTracker({ steps = [], isActive }) {
  if (!isActive && steps.length === 0) return null;

  const activeIndex = PIPELINE.findIndex(a => {
    const s = getAgentStatus(a.key, steps);
    return s === 'active' || s === 'healing';
  });

  return (
    <div
      className="mb-3 rounded-xl border overflow-hidden"
      style={{
        borderColor: 'rgba(255,255,255,0.08)',
        background: 'rgba(255,255,255,0.02)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 border-b"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span className="relative flex h-1.5 w-1.5">
          {isActive && (
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-40"
              style={{ background: 'rgba(255,255,255,0.6)' }}
            />
          )}
          <span
            className="relative inline-flex rounded-full h-1.5 w-1.5"
            style={{ background: isActive ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.15)' }}
          />
        </span>
        <span
          className="text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Research Mode — Multi-Agent Crew
        </span>
      </div>

      {/* Pipeline steps */}
      <div className="flex items-start gap-0 px-3 py-2.5 overflow-x-auto">
        {PIPELINE.map((agent, i) => {
          const status = getAgentStatus(agent.key, steps);
          const latestStep = getLatestStep(agent.key, steps);
          const isLast = i === PIPELINE.length - 1;
          const isPastActive = activeIndex !== -1 && i < activeIndex;

          // Colours by status — monochrome
          const iconBg =
            status === 'done'    ? 'rgba(255,255,255,0.08)' :
            status === 'active'  ? 'rgba(255,255,255,0.12)' :
            status === 'healing' ? 'rgba(255,255,255,0.10)' :
                                   'rgba(255,255,255,0.04)';
          const iconBorder =
            status === 'done'    ? 'rgba(255,255,255,0.25)' :
            status === 'active'  ? 'rgba(255,255,255,0.45)' :
            status === 'healing' ? 'rgba(255,255,255,0.30)' :
                                   'rgba(255,255,255,0.08)';
          const labelColor =
            status === 'done'    ? 'rgba(255,255,255,0.40)' :
            status === 'active'  ? 'rgba(255,255,255,0.90)' :
            status === 'healing' ? 'rgba(255,255,255,0.70)' :
                                   'rgba(255,255,255,0.18)';

          return (
            <div key={agent.key} className="flex items-center flex-shrink-0">
              {/* Agent node */}
              <div className="flex flex-col items-center" style={{ minWidth: '72px' }}>
                {/* Status icon */}
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center mb-1 transition-all duration-300"
                  style={{ background: iconBg, border: `1px solid ${iconBorder}` }}
                >
                  {status === 'done' && (
                    <Check className="w-3 h-3" style={{ color: 'rgba(255,255,255,0.5)' }} />
                  )}
                  {status === 'active' && (
                    <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'rgba(255,255,255,0.85)' }} />
                  )}
                  {status === 'healing' && (
                    <Wrench className="w-3 h-3 animate-pulse" style={{ color: 'rgba(255,255,255,0.7)' }} />
                  )}
                  {status === 'pending' && (
                    <span className="w-1 h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.15)' }} />
                  )}
                </div>

                {/* Agent short name */}
                <span
                  className="text-[9px] font-semibold text-center leading-tight tracking-wide"
                  style={{ color: labelColor }}
                >
                  {agent.short}
                </span>

                {/* Latest step message — only when active or healing */}
                {(status === 'active' || status === 'healing') && latestStep && (
                  <span
                    className="text-[8px] text-center mt-0.5 leading-tight max-w-[80px] truncate"
                    style={{ color: 'rgba(255,255,255,0.25)' }}
                    title={cleanStep(latestStep)}
                  >
                    {cleanStep(latestStep)}
                  </span>
                )}
              </div>

              {/* Connector line */}
              {!isLast && (
                <div
                  className="mx-1 h-px w-5 flex-shrink-0 mt-[-14px]"
                  style={{
                    background: isPastActive
                      ? 'rgba(255,255,255,0.20)'
                      : 'rgba(255,255,255,0.06)',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
