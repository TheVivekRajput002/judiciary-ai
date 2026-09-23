import type { ConflictBlock } from '../types'

export function ConflictNotice({ conflicts }: { conflicts: ConflictBlock[] }) {
  if (conflicts.length === 0) return null

  return (
    <div
      className="mt-4 rounded-lg p-4"
      style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-warning)' }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span style={{ color: 'var(--color-warning)' }}>⚠</span>
        <span className="text-sm font-semibold" style={{ color: 'var(--color-warning)' }}>
          Conflicting Legal Authorities Detected
        </span>
      </div>

      {conflicts.map((conflict, i) => (
        <div key={i} className="mb-4 last:mb-0">
          <p className="text-xs mb-3" style={{ color: 'var(--color-text-secondary)' }}>
            {conflict.description}
          </p>
          <div className="grid grid-cols-2 gap-3">
            {/* Position A */}
            <div
              className="rounded p-3"
              style={{
                background: 'var(--color-bg-surface)',
                borderTop: '2px solid var(--color-info)',
              }}
            >
              <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--color-info)' }}>
                Position A
              </div>
              <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
                {conflict.position_a}
              </p>
              {conflict.sources_a.map((s, j) => (
                <div key={j} className="text-xs mt-1 font-mono" style={{ color: 'var(--color-text-muted)' }}>
                  — {s}
                </div>
              ))}
            </div>

            {/* Position B */}
            <div
              className="rounded p-3"
              style={{
                background: 'var(--color-bg-surface)',
                borderTop: '2px solid var(--color-accent)',
              }}
            >
              <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--color-accent)' }}>
                Position B
              </div>
              <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
                {conflict.position_b}
              </p>
              {conflict.sources_b.map((s, j) => (
                <div key={j} className="text-xs mt-1 font-mono" style={{ color: 'var(--color-text-muted)' }}>
                  — {s}
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
