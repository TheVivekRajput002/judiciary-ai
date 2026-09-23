import type { PipelineStage } from '../types'
import { useChatStore } from '../store/useChatStore'

const STAGE_ORDER: PipelineStage[] = [
  'Understand', 'Plan', 'Retrieve', 'Research', 'Reason', 'Synthesize', 'Cite',
]

export function PipelineProgressIndicator() {
  const stages = useChatStore((s) => s.currentStages)
  if (stages.length === 0) return null

  const stageMap = Object.fromEntries(stages.map((s) => [s.stage, s]))

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 border-b text-xs overflow-x-auto"
      style={{ borderColor: 'var(--color-bg-border)', background: 'var(--color-bg-surface)' }}
    >
      {STAGE_ORDER.map((stage, i) => {
        const event = stageMap[stage]
        const isRunning = event?.status === 'running'
        const isDone = event?.status === 'done'
        const isError = event?.status === 'error'

        return (
          <div key={stage} className="flex items-center gap-1.5 shrink-0">
            {i > 0 && (
              <span style={{ color: 'var(--color-bg-border)' }}>→</span>
            )}
            <span
              className={`flex items-center gap-1 transition-all duration-150 ${
                isRunning ? 'animate-gold-pulse' : ''
              }`}
              style={{
                color: isDone
                  ? 'var(--color-success)'
                  : isRunning
                  ? 'var(--color-accent)'
                  : isError
                  ? 'var(--color-error)'
                  : 'var(--color-text-muted)',
                fontWeight: isRunning || isDone ? 500 : 400,
              }}
            >
              {isDone && <span>✓</span>}
              {isError && <span>✗</span>}
              {stage}
            </span>
          </div>
        )
      })}

      {/* Gold progress bar */}
      <div
        className="ml-auto shrink-0 w-20 h-0.5 rounded overflow-hidden"
        style={{ background: 'var(--color-bg-border)' }}
      >
        <div
          className="h-full rounded transition-all duration-500"
          style={{
            background: 'var(--color-accent)',
            width: `${(stages.filter((s) => s.status === 'done').length / STAGE_ORDER.length) * 100}%`,
          }}
        />
      </div>
    </div>
  )
}
