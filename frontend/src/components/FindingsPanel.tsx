import { useResearchStore } from '../store/useResearchStore'
import type { ResearchEntity } from '../types'

const ENTITY_STYLES: Record<ResearchEntity['entity_type'], { bg: string; color: string; label: string }> = {
  case: { bg: 'rgba(201,168,76,0.1)', color: 'var(--color-accent)', label: 'Case' },
  statute: { bg: 'rgba(91,141,238,0.1)', color: 'var(--color-info)', label: 'Statute' },
  issue: { bg: 'rgba(62,207,142,0.1)', color: 'var(--color-success)', label: 'Issue' },
  authority: { bg: 'rgba(245,166,35,0.1)', color: 'var(--color-warning)', label: 'Authority' },
}

export function FindingsPanel() {
  const entities = useResearchStore((s) => s.entities)
  if (entities.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      <div
        className="text-xs uppercase tracking-widest"
        style={{ color: 'var(--color-text-muted)' }}
      >
        Findings
      </div>
      <div className="flex flex-col gap-1.5">
        {entities.map((entity) => {
          const style = ENTITY_STYLES[entity.entity_type]
          return (
            <div
              key={entity.id}
              className="flex items-start gap-2 rounded px-2.5 py-1.5 text-xs"
              style={{ background: style.bg }}
              title={entity.summary}
            >
              <span
                className="shrink-0 rounded-full px-1.5 py-0.5 text-xs"
                style={{ color: style.color, fontWeight: 600, fontSize: '10px' }}
              >
                {style.label}
              </span>
              <span
                className="truncate"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {entity.name}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
