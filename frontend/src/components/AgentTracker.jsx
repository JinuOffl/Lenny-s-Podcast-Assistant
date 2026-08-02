/**
 * AgentTracker.jsx — Live pipeline visualization shown above streaming responses
 * in Research Mode.
 *
 * Displays the 5-agent pipeline as a horizontal sequence:
 *   OrchestratorAgent → ResearchAgent → WriterAgent → ArtifactAgent → ValidatorAgent
 *
 * Each agent can be: pending | active | done | healing
 *
 * Props:
 *   steps: Array<{agent: string, step: string}>  — accumulated from SSE events
 *   isActive: bool — whether Research Mode is streaming
 */
import { Check, Loader2, AlertTriangle } from 'lucide-react';

const PIPELINE = [
  { key: 'OrchestratorAgent', label: 'Orchestrator', short: 'Plan' },
  { key: 'ResearchAgent',     label: 'Research',     short: 'Search' },
  { key: 'WriterAgent',       label: 'Writer',       short: 'Write' },
  { key: 'ArtifactAgent',     label: 'Artifact',     short: 'Build' },
  { key: 'ValidatorAgent',    label: 'Validator',    short: 'QC' },
];

function getAgentStatus(agentKey, steps) {
  const agentSteps = steps.filter(s => s.agent === agentKey);
  if (agentSteps.length === 0) return 'pending';

  const lastStep = agentSteps[agentSteps.length - 1].step || '';
  if (lastStep.includes('🔧') || lastStep.includes('Self-healing')) return 'healing';
  if (lastStep.includes('✅') || lastStep.includes('🏁')) return 'done';
  return 'active';
}

function getLatestStep(agentKey, steps) {
  const agentSteps = steps.filter(s => s.agent === agentKey);
  return agentSteps[agentSteps.length - 1]?.step || '';
}

export default function AgentTracker({ steps = [], isActive }) {
  if (!isActive && steps.length === 0) return null;

  // Find which agent is currently active
  const activeAgent = [...PIPELINE].reverse().find(a => {
    const status = getAgentStatus(a.key, steps);
    return status === 'active' || status === 'healing';
  });

  return (
    <div
      className="mb-3 rounded-xl border overflow-hidden"
      style={{
        borderColor: 'rgba(249,115,22,0.2)',
        background: 'rgba(249,115,22,0.04)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 border-b"
        style={{ borderColor: 'rgba(249,115,22,0.15)' }}
      >
        <span className="relative flex h-1.5 w-1.5">
          {isActive && (
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
              style={{ background: 'rgb(249,115,22)' }}
            />
          )}
          <span
            className="relative inline-flex rounded-full h-1.5 w-1.5"
            style={{ background: isActive ? 'rgb(249,115,22)' : 'rgba(249,115,22,0.4)' }}
          />
        </span>
        <span className="text-[10px] font-semibold tracking-widest uppercase"
          style={{ color: 'rgba(249,115,22,0.8)' }}>
          Research Mode — Multi-Agent Crew
        </span>
      </div>

      {/* Pipeline steps */}
      <div className="flex items-start gap-0 px-3 py-2.5 overflow-x-auto">
        {PIPELINE.map((agent, i) => {
          const status = getAgentStatus(agent.key, steps);
          const latestStep = getLatestStep(agent.key, steps);
          const isLast = i === PIPELINE.length - 1;

          return (
            <div key={agent.key} className="flex items-center flex-shrink-0">
              {/* Agent node */}
              <div className="flex flex-col items-center" style={{ minWidth: '72px' }}>
                {/* Status icon */}
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center mb-1 transition-all duration-300"
                  style={{
                    background:
                      status === 'done'    ? 'rgba(74,222,128,0.15)' :
                      status === 'active'  ? 'rgba(249,115,22,0.2)'  :
                      status === 'healing' ? 'rgba(251,191,36,0.2)'  :
                                            'rgba(255,255,255,0.05)',
                    border: `1px solid ${
                      status === 'done'    ? 'rgba(74,222,128,0.4)'  :
                      status === 'active'  ? 'rgba(249,115,22,0.5)'  :
                      status === 'healing' ? 'rgba(251,191,36,0.4)'  :
                                            'rgba(255,255,255,0.1)'
                    }`,
                  }}
                >
                  {status === 'done' && (
                    <Check className="w-3 h-3" style={{ color: 'rgb(74,222,128)' }} />
                  )}
                  {status === 'active' && (
                    <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'rgb(249,115,22)' }} />
                  )}
                  {status === 'healing' && (
                    <AlertTriangle className="w-3 h-3 animate-pulse" style={{ color: 'rgb(251,191,36)' }} />
                  )}
                  {status === 'pending' && (
                    <span className="w-1 h-1 rounded-full bg-white/20" />
                  )}
                </div>

                {/* Agent name */}
                <span
                  className="text-[9px] font-semibold text-center leading-tight"
                  style={{
                    color:
                      status === 'done'    ? 'rgba(74,222,128,0.8)'  :
                      status === 'active'  ? 'rgb(249,115,22)'        :
                      status === 'healing' ? 'rgb(251,191,36)'        :
                                            'rgba(255,255,255,0.25)',
                  }}
                >
                  {agent.short}
                </span>

                {/* Latest step message (only for active/healing) */}
                {(status === 'active' || status === 'healing') && latestStep && (
                  <span
                    className="text-[8px] text-center mt-0.5 leading-tight max-w-[80px] truncate"
                    style={{ color: 'rgba(255,255,255,0.35)' }}
                    title={latestStep}
                  >
                    {latestStep.replace(/^[^\s]+ /, '')}
                  </span>
                )}
              </div>

              {/* Connector arrow */}
              {!isLast && (
                <div
                  className="mx-1 h-px w-5 flex-shrink-0 mt-[-14px]"
                  style={{
                    background: i < PIPELINE.findIndex(a => getAgentStatus(a.key, steps) === 'active' || getAgentStatus(a.key, steps) === 'pending')
                      ? 'rgba(249,115,22,0.3)'
                      : 'rgba(255,255,255,0.08)',
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
